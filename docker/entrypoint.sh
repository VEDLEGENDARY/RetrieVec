#!/bin/sh
set -eu

python -m retrievec.registry.cli migrate
retrievald rpc --store "$RETRIEVEC_STORE" --listen 127.0.0.1:8092 &
rpc_pid=$!
python -m retrievec.app.worker &
worker_pid=$!
python -m retrievec.app.research_worker &
research_pid=$!
python -m retrievec.app.main &
api_pid=$!

shutdown() {
  kill "$api_pid" "$rpc_pid" "$worker_pid" "$research_pid" 2>/dev/null || true
  wait "$api_pid" "$rpc_pid" "$worker_pid" "$research_pid" 2>/dev/null || true
}
trap shutdown EXIT INT TERM
wait "$api_pid"
