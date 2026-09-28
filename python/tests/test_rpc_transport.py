import os
import unittest
from unittest.mock import patch

from retrievec.client.rpc import RPCClient


class TransportTests(unittest.TestCase):
    def test_remote_plaintext_and_partial_tls_are_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            for address in ("10.0.0.1:8092", "retrieval:8092", "[::]:8092"):
                with self.assertRaises(ValueError):
                    RPCClient(address, "token")
        with patch.dict(os.environ, {"RETRIEVEC_RPC_TLS_CA": "missing"}, clear=True):
            with self.assertRaises(ValueError):
                RPCClient("127.0.0.1:8092", "token")

    def test_principal_control_characters_are_rejected_before_channel_creation(self):
        with self.assertRaises(ValueError):
            RPCClient("127.0.0.1:8092", "token", principal="owner\nheader")
