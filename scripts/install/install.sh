#!/usr/bin/env bash
# Back-compat wrapper — prefer scripts/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec bash "$ROOT/scripts/setup.sh" "$@"
