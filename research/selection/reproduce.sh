#!/bin/sh
# Regenerate the selector and chronological experiments.
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
uv run --python 3.12 --with apsw==3.53.1.0 python -B research/selection/test_review.py
uv run --locked --script research/selection/run.py --out "$scratch/results"
uv run --python 3.12 python - research/selection/results "$scratch/results" <<'PY'
import gzip
from pathlib import Path
import sys
archive, run = map(Path,sys.argv[1:])
if sorted(p.name for p in archive.iterdir()) != sorted(p.name for p in run.iterdir()):
    sys.exit("Selection archive inventory differs")
for p in sorted(archive.iterdir()):
    def content(path):
        data = path.read_bytes()
        return gzip.decompress(data) if path.suffix == ".gz" else data
    if content(p) != content(run/p.name):
        sys.exit(f"Selection archive differs: {p.name}")
    print(f"Verified {p.name}")
PY
