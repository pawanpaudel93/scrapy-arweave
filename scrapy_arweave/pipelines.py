import functools
import hashlib
import logging
import os
import warnings
from contextlib import suppress
from io import BytesIO
from urllib.parse import urlparse

from itemadapter import ItemAdapter
from scrapy.exceptions import NotConfigured, ScrapyDeprecationWarning
from scrapy.http import Request
from scrapy.pipelines.files import FileException
from scrapy.pipelines.files import FilesPipeline as ParentFilesPipeline
from scrapy.pipelines.files import FSFilesStore
from scrapy.pipelines.images import ImageException
from scrapy.settings import Settings
from scrapy.utils.log import failure_to_exc_info
from scrapy.utils.python import get_func_args, to_bytes
from scrapy.utils.request import referer_str
from twisted.internet import defer, threads

logger = logging.getLogger(__name__)


class ArweaveFilesStore(FSFilesStore):
    WALLET_JWK = ""
    GATEWAY_URL = ""

    def __init__(self, basedir):
        from .client import ArweaveStorageClient

        super().__init__(basedir)
        self.client = ArweaveStorageClient(self.WALLET_JWK, self.GATEWAY_URL)

    def persist_file(self, path, buf, info, meta=None, headers=None):
        absolute_path = self._get_filesystem_path(path)
        super().persist_file(path, buf, info, meta, headers)
        file_hash = self.client.calculate_hash(absolute_path)
        dfd = threads.deferToThread(self.client.upload, absolute_path, buf.getvalue(), file_hash)
        return dfd

    def stat_file(self, path, info):
        absolute_path = self._get_filesystem_path(path)
        file_hash = self.client.calculate_hash(absolute_path)
        dfd = threads.deferToThread(self.client.get_tx_id, file_hash)
        return dfd.addCallback(lambda tx_id: {"tx_id": tx_id})


class FilesPipeline(ParentFilesPipeline):
    """Custom Files Abstract pipeline that implement the file downloading"""

    STORE_SCHEMES = {
        '': ArweaveFilesStore,
        'ar': ArweaveFilesStore,
    }

    @classmethod
    def init_settings(cls, settings):
        arweave_store = cls.STORE_SCHEMES['ar']
        arweave_store.WALLET_JWK = settings['WALLET_JWK']
        arweave_store.GATEWAY_URL = settings["GATEWAY_URL"] or "https://arweave.net"

    @classmethod
    def from_settings(cls, settings):
        cls.init_settings(settings)
        store_uri = settings['FILES_STORE']
        return cls(store_uri, settings=settings)

    def _get_store(self, uri):
        if os.path.isabs(uri):  # to support win32 paths like: C:\\some\dir
            scheme = "ar"
        else:
            scheme = urlparse(uri).scheme
        store_cls = self.STORE_SCHEMES[scheme]
        return store_cls(uri)

    def media_to_download(self, request, info, *, item=None):
        def _onsuccess(result):
            if not result:
                return  # returning None force download

            referer = referer_str(request)
            logger.debug(
                'File (uptodate): Downloaded %(medianame)s from %(request)s ' 'referred in <%(referer)s>',
                {'medianame': self.MEDIA_NAME, 'request': request, 'referer': referer},
                extra={'spider': info.spider},
            )
            self.inc_stats(info.spider, 'uptodate')

            tx_id = result.get('tx_id', None)
            permalink = self.store.client.get_url(tx_id)
            return {'url': request.url, 'tx_id': tx_id, "permalink": permalink}

        path = self.file_path(request, info=info, item=item)
        dfd = defer.maybeDeferred(self.store.stat_file, path, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(
            lambda f: logger.error(
                self.__class__.__name__ + '.store.stat_file',
                exc_info=failure_to_exc_info(f),
                extra={'spider': info.spider},
            )
        )
        return dfd

    def media_downloaded(self, response, request, info, *, item=None):
        referer = referer_str(request)

        if response.status != 200:
            logger.warning(
                'File (code: %(status)s): Error downloading file from ' '%(request)s referred in <%(referer)s>',
                {'status': response.status, 'request': request, 'referer': referer},
                extra={'spider': info.spider},
            )
            raise FileException('download-error')

        if not response.body:
            logger.warning(
                'File (empty-content): Empty file from %(request)s referred ' 'in <%(referer)s>: no-content',
                {'request': request, 'referer': referer},
                extra={'spider': info.spider},
            )
            raise FileException('empty-content')

        status = 'cached' if 'cached' in response.flags else 'downloaded'
        logger.debug(
            'File (%(status)s): Downloaded file from %(request)s referred in ' '<%(referer)s>',
            {'status': status, 'request': request, 'referer': referer},
            extra={'spider': info.spider},
        )
        self.inc_stats(info.spider, status)

        try:
            dfd = self.file_downloaded(response, request, info, item=item)

            def _onsuccess(tx_id):
                permalink = self.store.client.get_url(tx_id)
                return {'url': request.url, 'tx_id': tx_id, "permalink": permalink}

            if dfd:
                dfd.addCallbacks(_onsuccess, lambda _: None)
            return dfd
        except FileException as exc:
            logger.warning(
                'File (error): Error processing file from %(request)s ' 'referred in <%(referer)s>: %(errormsg)s',
                {'request': request, 'referer': referer, 'errormsg': str(exc)},
                extra={'spider': info.spider},
                exc_info=True,
            )
            raise
        except Exception as exc:
            logger.error(
                'File (unknown-error): Error processing file from %(request)s ' 'referred in <%(referer)s>',
                {'request': request, 'referer': referer},
                exc_info=True,
                extra={'spider': info.spider},
            )
            raise FileException(str(exc))

    def file_downloaded(self, response, request, info, *, item=None):
        path = self.file_path(request, response=response, info=info, item=item)
        buf = BytesIO(response.body)
        buf.seek(0)
        return self.store.persist_file(path, buf, info)


class ImagesPipeline(FilesPipeline):
    """Custom Image Abstract pipeline that implement the image thumbnail generation logic"""

    MEDIA_NAME = 'image'

    # Uppercase attributes kept for backward compatibility with code that subclasses
    # ImagesPipeline. They may be overridden by settings.
    MIN_WIDTH = 0
    MIN_HEIGHT = 0
    EXPIRES = 90
    THUMBS = {}
    DEFAULT_IMAGES_URLS_FIELD = 'image_urls'
    DEFAULT_IMAGES_RESULT_FIELD = 'images'

    def __init__(self, store_uri, download_func=None, settings=None):
        try:
            from PIL import Image

            self._Image = Image
        except ImportError:
            raise NotConfigured('ImagesPipeline requires installing Pillow 4.0.0 or later')

        super().__init__(store_uri, settings=settings, download_func=download_func)

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        resolve = functools.partial(self._key_for_pipe, base_class_name="ImagesPipeline", settings=settings)
        self.expires = settings.getint(resolve("IMAGES_EXPIRES"), self.EXPIRES)

        if not hasattr(self, "IMAGES_RESULT_FIELD"):
            self.IMAGES_RESULT_FIELD = self.DEFAULT_IMAGES_RESULT_FIELD
        if not hasattr(self, "IMAGES_URLS_FIELD"):
            self.IMAGES_URLS_FIELD = self.DEFAULT_IMAGES_URLS_FIELD

        self.images_urls_field = settings.get(resolve('IMAGES_URLS_FIELD'), self.IMAGES_URLS_FIELD)
        self.images_result_field = settings.get(resolve('IMAGES_RESULT_FIELD'), self.IMAGES_RESULT_FIELD)
        self.min_width = settings.getint(resolve('IMAGES_MIN_WIDTH'), self.MIN_WIDTH)
        self.min_height = settings.getint(resolve('IMAGES_MIN_HEIGHT'), self.MIN_HEIGHT)
        self.thumbs = settings.get(resolve('IMAGES_THUMBS'), self.THUMBS)

        self._deprecated_convert_image = None

    @classmethod
    def from_settings(cls, settings):
        cls.init_settings(settings)
        store_uri = settings['IMAGES_STORE']
        return cls(store_uri, settings=settings)

    def file_downloaded(self, response, request, info, *, item=None):
        return self.image_downloaded(response, request, info, item=item)

    def image_downloaded(self, response, request, info, *, item=None):
        result = None
        for path, image, buf in self.get_images(response, request, info, item=item):
            buf.seek(0)
            width, height = image.size
            result = self.store.persist_file(
                path,
                buf,
                info,
                meta={'width': width, 'height': height},
                headers={'Content-Type': 'image/jpeg'},
            )
        return result

    def get_images(self, response, request, info, *, item=None):
        path = self.file_path(request, response=response, info=info, item=item)
        orig_image = self._Image.open(BytesIO(response.body))

        width, height = orig_image.size
        if width < self.min_width or height < self.min_height:
            raise ImageException("Image too small " f"({width}x{height} < " f"{self.min_width}x{self.min_height})")

        if self._deprecated_convert_image is None:
            self._deprecated_convert_image = 'response_body' not in get_func_args(self.convert_image)
            if self._deprecated_convert_image:
                warnings.warn(
                    f'{self.__class__.__name__}.convert_image() method overriden in a deprecated way, '
                    'overriden method does not accept response_body argument.',
                    category=ScrapyDeprecationWarning,
                )

        if self._deprecated_convert_image:
            image, buf = self.convert_image(orig_image)
        else:
            image, buf = self.convert_image(orig_image, response_body=BytesIO(response.body))
        yield path, image, buf

        for thumb_id, size in self.thumbs.items():
            thumb_path = self.thumb_path(request, thumb_id, response=response, info=info, item=item)
            if self._deprecated_convert_image:
                thumb_image, thumb_buf = self.convert_image(image, size)
            else:
                thumb_image, thumb_buf = self.convert_image(image, size, buf)
            yield thumb_path, thumb_image, thumb_buf

    def convert_image(self, image, size=None, response_body=None):
        if response_body is None:
            warnings.warn(
                f'{self.__class__.__name__}.convert_image() method called in a deprecated way, '
                'method called without response_body argument.',
                category=ScrapyDeprecationWarning,
                stacklevel=2,
            )

        if image.format == 'PNG' and image.mode == 'RGBA':
            background = self._Image.new('RGBA', image.size, (255, 255, 255))
            background.paste(image, image)
            image = background.convert('RGB')
        elif image.mode == 'P':
            image = image.convert("RGBA")
            background = self._Image.new('RGBA', image.size, (255, 255, 255))
            background.paste(image, image)
            image = background.convert('RGB')
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        if size:
            image = image.copy()
            try:
                # Image.Resampling.LANCZOS was added in Pillow 9.1.0
                # remove this try except block,
                # when updating the minimum requirements for Pillow.
                resampling_filter = self._Image.Resampling.LANCZOS
            except AttributeError:
                resampling_filter = self._Image.ANTIALIAS
            image.thumbnail(size, resampling_filter)
        elif response_body is not None and image.format == 'JPEG':
            return image, response_body

        buf = BytesIO()
        image.save(buf, 'JPEG')
        return image, buf

    def get_media_requests(self, item, info):
        urls = ItemAdapter(item).get(self.images_urls_field, [])
        return [Request(u) for u in urls]

    def item_completed(self, results, item, info):
        with suppress(KeyError):
            ItemAdapter(item)[self.images_result_field] = [x for ok, x in results if ok]
        return item

    def file_path(self, request, response=None, info=None, *, item=None):
        image_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
        return f'full/{image_guid}.jpg'

    def thumb_path(self, request, thumb_id, response=None, info=None, *, item=None):
        thumb_guid = hashlib.sha1(to_bytes(request.url)).hexdigest()
        return f'thumbs/{thumb_id}/{thumb_guid}.jpg'
