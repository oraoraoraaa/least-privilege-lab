#!/bin/sh
# Verify both studies from a clean branch checkout.
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
sh research/classroom/reproduce.sh "$@"
uv run --python 3.12 --with 'z3-solver==5.4.1.0' python -B research/registry/test_refine.py
uv run --python 3.12 python -B research/registry/run_pilot.py \
    --check research/registry/pilot-results.json
