import logging
from urllib.parse import urlparse

from scrapy.extensions.feedexport import BlockingFeedStorage
from scrapy.utils.project import get_project_settings

logger = logging.getLogger(__name__)


class ArweaveFeedStorage(BlockingFeedStorage):
    def _store_in_thread(self, file):
        file.seek(0)
        tx_id = self.client.upload(self.file_name, file)
        permalink = self.client.get_url(tx_id)
        logging.info(permalink)
        file.close()


class ArweaveStorageFeedStorage(ArweaveFeedStorage):
    def __init__(self, uri, *, feed_options=None):
        settings = get_project_settings()
        from .client import ArweaveStorageClient

        u = urlparse(uri)
        self.file_name = u.path if u.path else u.netloc
        gateway_url = settings.get("GATEWAY_URL", "https://arweave.net")
        wallet_jwk = settings.get("WALLET_JWK")
        self.client = ArweaveStorageClient(wallet_jwk, gateway_url)


def get_feed_storages():
    return {
        '': 'scrapy_arweave.feedexport.ArweaveStorageFeedStorage',
        'arweave': 'scrapy_arweave.feedexport.ArweaveStorageFeedStorage',
    }
