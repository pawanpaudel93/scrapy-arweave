import os
from pathlib import Path

from decouple import config

from ..client import ArweaveStorageClient


def test_upload():
    file_path = os.path.join(Path(__file__).resolve().parent, "test.txt")
    ws_client = ArweaveStorageClient(config("WALLET_JWK"), "https://arweave.net")
    tx_id = ws_client.upload("test.txt", open(file_path, "rb"))
    print("tx_id: ", tx_id)
    assert type(tx_id) == str
