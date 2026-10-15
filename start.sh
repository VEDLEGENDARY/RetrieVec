#!/bin/sh
# Run with: sh start.sh [start|doctor|status|logs|stop]
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
action=${1:-start}
case "$action" in start|doctor|status|logs|stop) ;; *) printf 'Usage: sh start.sh [start|doctor|status|logs|stop]\n' >&2; exit 2 ;; esac
command -v docker >/dev/null 2>&1 || { printf 'Install and start Docker Desktop or Docker Engine with the Compose plugin, then retry.\n' >&2; exit 1; }
docker compose version || { printf 'Docker Compose is missing. Update Docker Desktop or install the Compose plugin.\n' >&2; exit 1; }
engine_type=$(docker info --format '{{.OSType}}' 2>/dev/null) || { printf 'Docker is not running. Start Docker Desktop/Engine, wait for it to be ready, and retry.\n' >&2; exit 1; }
[ "$engine_type" = linux ] || { printf 'Select Linux containers in Docker Desktop and retry.\n' >&2; exit 1; }
docker compose -f compose.yaml config --quiet
compose() {
    docker compose -f compose.yaml "$@" || { printf 'Compose failed. Run sh start.sh logs, fix the reported issue, and retry sh start.sh.\n' >&2; exit 1; }
}
case "$action" in
    doctor) printf 'Docker, Linux containers, and Compose configuration are ready. Start with sh start.sh.\n' ;;
    status) compose ps -a ;;
    logs) compose logs --tail=100 workspace identity postgres init ;;
    stop) compose down; printf 'Stopped. Your account, papers, and model cache are preserved. Run sh start.sh to return.\n' ;;
    start)
        printf 'Starting RetrieVec. The first build and model download may take several minutes.\nPorts 8000 and 8080 must be free. Waiting for the workspace and sign-in service.\n'
        compose up --build --wait --wait-timeout 900
        printf '\nOpen http://127.0.0.1:8000. Choose Sign in, then Register to create your local account.\nTry the SciFact starter, or create a private collection and upload your papers.\n'
        ;;
esac
