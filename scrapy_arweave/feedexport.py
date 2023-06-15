import logging
from urllib.parse import urlparse

from scrapy.extensions.feedexport import BlockingFeedStorage
from scrapy.utils.project import get_project_settings

logger = logging.getLogger(__name__)


class ArweaveFeedStorage(BlockingFeedStorage):
    def __init__(self, uri, *, feed_options=None):
        settings = get_project_settings()
        from .client import ArweaveStorageClient

        u = urlparse(uri)
        self.file_name = u.path if u.path else u.netloc
        gateway_url = settings.get("GATEWAY_URL", "https://arweave.net")
        wallet_jwk = settings.get("WALLET_JWK")
        self.client = ArweaveStorageClient(wallet_jwk, gateway_url)

    def _store_in_thread(self, file):
        file.seek(0)
        try:
            file_hash = self.client.calculate_hash(file.name)
            tx_id = self.client.get_tx_id(file_hash)
        except:
            tx_id = self.client.upload(file.name, file.read())
        permalink = self.client.get_url(tx_id)
        logging.info(permalink)
        file.close()


def get_feed_storages():
    return {
        '': 'scrapy_arweave.feedexport.ArweaveFeedStorage',
        'ar': 'scrapy_arweave.feedexport.ArweaveFeedStorage',
    }
