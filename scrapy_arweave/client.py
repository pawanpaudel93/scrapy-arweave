import hashlib
import mimetypes
import os
from urllib.parse import urljoin

from ar import ANS104DataItemHeader, DataItem, Wallet
from ar.transaction import Transaction
from ar.utils.transaction_uploader import create_tag, get_uploader
from bundlr import Node


class ArweaveStorageClient:
    wallet = None

    def __init__(self, wallet_jwk, gateway_url) -> None:
        self.GATEWAY_URL = gateway_url
        self.load_wallet(wallet_jwk)

    def calculate_hash(self, filepath, algorithm='sha256', chunk_size=65536):
        """
        Calculate the hash of a file using the specified algorithm.
        Returns the hash value as a hexadecimal string.
        """
        # Create a hash object using the specified algorithm
        hash_object = hashlib.new(algorithm)

        # Read the file in chunks and update the hash object
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                hash_object.update(data)

        # Get the hexadecimal representation of the hash value
        hash_value = hash_object.hexdigest()

        return hash_value

    def load_wallet(self, wallet_jwk):
        if os.path.isfile(wallet_jwk):
            self.wallet = Wallet(wallet_jwk)
            self.wallet.api_url = self.GATEWAY_URL
        else:
            self.wallet = Wallet.from_data(wallet_jwk)
            self.wallet.api_url = self.GATEWAY_URL

    def upload(self, file_path, file):
        mime_type, _ = mimetypes.guess_type(file_path)
        try:
            tags = [create_tag("Content-Type", mime_type, self.format == 2)]
            dataitem = DataItem(data=file, header=ANS104DataItemHeader(tags=tags))
            dataitem.sign(self.wallet.rsa)
            node = Node()
            result = node.send_tx(dataitem.tobytes())
            txid = result['id']
            return txid
        except:
            pass

        try:
            with open(file_path, 'rb', buffering=0) as file_handler:
                tx = Transaction(self.wallet, file_handler=file_handler, file_path=file_path)
                tx.api_url = self.GATEWAY_URL
                tx.add_tag('Content-Type', mime_type)
                tx.sign()

                uploader = get_uploader(tx, file_handler)

                while not uploader.is_complete:
                    uploader.upload_chunk()
                return tx.id

        except:
            pass

        raise Exception("Upload Error")

    def get_url(self, tx_id):
        return urljoin(self.GATEWAY_URL, tx_id)
