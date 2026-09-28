#!/bin/sh
set -eu

exec python -m retrievec.runtime "$@"
