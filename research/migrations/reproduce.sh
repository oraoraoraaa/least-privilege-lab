#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
uv run --locked --script research/migrations/run.py --out "$scratch"
uv run --python 3.12 python - research/migrations/results "$scratch" <<'PY'
import gzip
from pathlib import Path
import sys
archive, actual = map(Path, sys.argv[1:])
if {p.name for p in archive.iterdir()} != {p.name for p in actual.iterdir()}:
    raise SystemExit("Migration evidence inventories differ")
for p in sorted(archive.iterdir()):
    def canonical(path):
        return gzip.decompress(path.read_bytes()) if path.suffix==".gz" else path.read_bytes()
    if canonical(p)!=canonical(actual/p.name):
        raise SystemExit(f"Migration disagreement: {p.name}")
    print("Verified migration evidence",p.name)
PY
