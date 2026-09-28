"""Real encrypted channels: trusted client, wrong hostname and missing identity."""

import datetime
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import grpc
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from retrievec.client.rpc import RPCClient
from retrievec.retrieval.v1 import retrieval_pb2 as pb
from retrievec.retrieval.v1 import retrieval_pb2_grpc as rpc


def identity(name, *, ca=None, key=None, server=False):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca.subject if ca else subject)
        .public_key(private.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=ca is None, path_length=None), critical=True)
    )
    if server:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), False)
    certificate = builder.sign(key or private, hashes.SHA256())
    return certificate, private


def pem(certificate, key):
    return certificate.public_bytes(serialization.Encoding.PEM), key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


class Service(rpc.RetrievalServicer):
    def GetSnapshotInfo(self, request, context):
        metadata = dict(context.invocation_metadata())
        if metadata.get("authorization") != "Bearer test-token":
            context.abort(grpc.StatusCode.UNAUTHENTICATED, "credential required")
        return pb.SnapshotInfo(snapshot_id=request.snapshot_id)


class RPCTLSTests(unittest.TestCase):
    def test_mutual_identity_and_hostname_validation(self):
        ca, ca_key = identity("test-ca")
        server_cert, server_key = identity("localhost", ca=ca, key=ca_key, server=True)
        client_cert, client_key = identity("test-client", ca=ca, key=ca_key)
        ca_pem, _ = pem(ca, ca_key)
        cert_pem, key_pem = pem(server_cert, server_key)
        client_pem, client_private = pem(client_cert, client_key)
        with (
            ThreadPoolExecutor(max_workers=2) as executor,
            tempfile.TemporaryDirectory() as directory,
        ):
            server = grpc.server(executor)
            rpc.add_RetrievalServicer_to_server(Service(), server)
            port = server.add_secure_port(
                "127.0.0.1:0",
                grpc.ssl_server_credentials(
                    [(key_pem, cert_pem)],
                    root_certificates=ca_pem,
                    require_client_auth=True,
                ),
            )
            server.start()
            try:
                paths = {}
                for name, data in (("CA", ca_pem), ("CERT", client_pem), ("KEY", client_private)):
                    path = Path(directory) / name
                    path.write_bytes(data)
                    paths["RETRIEVEC_RPC_TLS_" + name] = str(path)
                with patch.dict(os.environ, paths):
                    client = RPCClient(f"localhost:{port}", "test-token", timeout=2)
                    try:
                        self.assertEqual(
                            client.info("collection", "snapshot").snapshot_id, "snapshot"
                        )
                    finally:
                        client.close()
                    wrong = RPCClient(f"127.0.0.1:{port}", "test-token", timeout=0.5)
                    try:
                        with self.assertRaises(grpc.RpcError):
                            wrong.info("collection", "snapshot")
                    finally:
                        wrong.close()
                with grpc.secure_channel(
                    f"localhost:{port}", grpc.ssl_channel_credentials(ca_pem)
                ) as channel:
                    with self.assertRaises(grpc.RpcError):
                        rpc.RetrievalStub(channel).GetSnapshotInfo(
                            pb.SnapshotRequest(), timeout=0.5
                        )
            finally:
                server.stop(0).wait()
