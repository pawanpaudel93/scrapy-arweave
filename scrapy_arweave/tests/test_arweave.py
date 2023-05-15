import os
from pathlib import Path

from ..client import ArweaveStorageClient


def test_upload():
    wallet_jwk = os.path.join(Path(__file__).resolve().parent, "test_jwk.json")
    file_path = os.path.join(Path(__file__).resolve().parent, "test.txt")
    arweave_client = ArweaveStorageClient(wallet_jwk, "http://localhost:1984")
    tx_id = arweave_client.upload(file_path, open(file_path, "rb").read())
    print("tx_id: ", tx_id)
    assert type(tx_id) == str
