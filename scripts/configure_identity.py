"""Generate an ignored local Keycloak realm with two random-password users."""

import json
import secrets
from pathlib import Path


def main():
    output = Path("artifacts/identity")
    output.mkdir(parents=True, exist_ok=True)
    realm = output / "retrievec-realm.json"
    if realm.exists():
        raise SystemExit("Identity configuration already exists; keep its users and passwords")
    passwords = {user: secrets.token_urlsafe(24) for user in ("researcher-a", "researcher-b")}
    realm.write_text(
        json.dumps(
            {
                "realm": "retrievec",
                "enabled": True,
                "registrationAllowed": False,
                "clients": [
                    {
                        "clientId": "retrievec",
                        "publicClient": True,
                        "standardFlowEnabled": True,
                        "directAccessGrantsEnabled": False,
                        "redirectUris": ["http://127.0.0.1:8000/auth/callback"],
                        "attributes": {"pkce.code.challenge.method": "S256"},
                    }
                ],
                "users": [
                    {
                        "username": user,
                        "enabled": True,
                        "credentials": [
                            {"type": "password", "value": password, "temporary": False}
                        ],
                    }
                    for user, password in passwords.items()
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (output / "local-passwords.json").write_text(json.dumps(passwords, indent=2), encoding="utf-8")
    print("Local users created. Read artifacts/identity/local-passwords.json; keep it private.")


if __name__ == "__main__":
    main()
