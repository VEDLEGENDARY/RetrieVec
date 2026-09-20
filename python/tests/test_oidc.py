import asyncio
import time
import unittest
from unittest.mock import AsyncMock

from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import RSAKey
from retrievec.app.config import Settings
from retrievec.app.main import create_app


class OIDCVerificationTests(unittest.TestCase):
    def test_signed_tokens_enforce_issuer_audience_nonce_expiry(self):
        app = create_app(Settings(dsn="unused", local_http=True))
        provider = app.state.oidc
        key = RSAKey.generate_key(2048, parameters={"kid": "test"})
        provider.fetch_jwk_set = AsyncMock(return_value={"keys": [key.as_dict(private=False)]})
        provider.load_server_metadata = AsyncMock(
            return_value={
                "issuer": app.state.settings.issuer,
                "id_token_signing_alg_values_supported": ["RS256"],
            }
        )
        valid = {
            "iss": app.state.settings.issuer,
            "aud": "retrievec",
            "sub": "a",
            "nonce": "expected",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
        }

        def verify(claims, signing_key=key):
            token = jwt.encode({"alg": "RS256", "kid": "test"}, claims, signing_key)
            return asyncio.run(
                provider.parse_id_token(
                    {"id_token": token},
                    nonce="expected",
                    claims_options={
                        "iss": {"essential": True, "value": valid["iss"]},
                        "nonce": {"essential": True, "value": "expected"},
                    },
                    leeway=0,
                )
            )

        self.assertEqual(verify(valid)["sub"], "a")
        for change in (
            {"iss": "https://other"},
            {"aud": "other"},
            {"nonce": "wrong"},
            {"exp": 1},
            {"nonce": "wrong", "nonce_supported": False},
        ):
            with self.subTest(change=change), self.assertRaises(JoseError):
                verify(valid | change)
        with self.assertRaises(JoseError):
            verify(valid, RSAKey.generate_key(2048))
