"""Generate local demo credentials once; never emit them to logs."""

import json
import os
import secrets
from pathlib import Path

root = Path("/settings")
root.mkdir(exist_ok=True)
config = root / "credentials.json"
if not config.exists():
    values = {key: secrets.token_urlsafe(36) for key in ("database", "read", "worker")}
    config.write_text(json.dumps(values))
    config.chmod(0o600)
    os.chown(config, 10001, 10001)
    (root / "postgres-password").write_text(values["database"])
    (root / "postgres-password").chmod(0o644)
store = Path("/store")
store.mkdir(exist_ok=True)
os.chown(store, 10001, 10001)
