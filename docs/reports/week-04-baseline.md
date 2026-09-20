# Persistent hybrid milestone

The implementation adds the specified compressed segment format, on-demand disk
postings, immutable retrieval snapshots, PostgreSQL active-pointer authority,
leased ingestion, authenticated generated RPC, exact CPU dense search and RRF.
Synthetic fixtures and model-fixture vectors are correctness evidence. Real-model
smoke results and human-reviewed relevance results are reported separately.

## Local setup

Install the pinned Go/Python versions and Python requirements as in the root README.
Start Docker Desktop. In PowerShell, set a fresh local database password and DSN:

```powershell
$env:RETRIEVEC_DB_PASSWORD = [guid]::NewGuid().ToString('N')
$env:RETRIEVEC_DSN = "postgresql://retrievec:$($env:RETRIEVEC_DB_PASSWORD)@127.0.0.1:55432/retrievec"
docker compose up -d --wait
$env:RETRIEVEC_TEST_DSN = $env:RETRIEVEC_DSN
.venv/Scripts/python.exe scripts/check.py
.venv/Scripts/python.exe scripts/demo_hybrid.py --output artifacts/runs/hybrid-fixture
.venv/Scripts/python.exe scripts/demo_hybrid.py --embedding minilm --output artifacts/runs/hybrid-model
```

Retain the password outside Git for subsequent sessions; an existing database
volume retains its original password. Use a separate database for tests. Linux
uses equivalent environment exports and .venv/bin/python, adding --race to checks.
The fixture demo uses no model download. The real-model demo downloads the pinned
public ONNX/tokenizer artifacts and runs locally. Neither uploads corpus text.

The demo ingests original synthetic documents through the leased worker, prepares
and activates a hybrid snapshot, captures all three modes, restarts Go and checks
ranking equality. Each output directory is new. evidence.json links exact model,
snapshot, capture hashes and environment; reviewed_quality_available remains false.
The integration suite exercises scope/control rejection, CAS conflicts, lease
expiry, corrupted artifacts and snapshot pinning. No automatic artifact GC runs.

Regenerate RPC bindings with scripts/generate_rpc.py after installing
protoc-gen-go@v1.36.12 and protoc-gen-go-grpc@v1.6.2. Both adapters share search code.

## Remaining evidence and next milestone

Owner-reviewed real-paper judgments and broader corpus coverage remain open.
Use scripts/compare_retrieval.py to capture a frozen three-mode run and generate
a draft review pool. No superiority claim is supported by fixture results.
Weeks 5–6 can add user authentication, interface and cited synthesis once these
evidence gates are resolved. Persistent files are immutable and retained; process
recovery tests do not establish power-loss durability.
