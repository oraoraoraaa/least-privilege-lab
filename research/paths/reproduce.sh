#!/bin/sh
# Regenerate each table from pinned SQL, then compare its canonical content.
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
study=research/paths
archive=$study/results
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
run=$scratch/results
cache=$root/build/path-inputs
uv run --python 3.12 python -B "$study/test_evaluate.py"
uv run --locked --script "$study/study.py" --cache "$cache" --out "$run"
uv run --python 3.12 python -B "$study/summarize.py" "$run" > "$run/summary.json"
uv run --python 3.12 python -B "$study/audit.py" "$run/traces.json" > "$run/audit.json"
uv run --python 3.12 --with 'apsw==3.53.1.0' python -B "$study/review_checks.py" "$run/traces.json" --cache "$cache" > "$run/review-checks.json"
uv run --python 3.12 python -B "$study/manuscript_checks.py" "$run" > "$run/manuscript-checks.json"
uv run --python 3.12 python - "$archive" "$run" <<'PY'
import gzip
from pathlib import Path
import sys

archive, run = map(Path, sys.argv[1:])
names = {p.name for p in archive.iterdir() if p.is_file()}
if names != {p.name for p in run.iterdir() if p.is_file()}:
    sys.exit("Archive and run have different output files")
for name in sorted(names):
    def read(folder):
        raw = (folder/name).read_bytes()
        return gzip.decompress(raw) if name.endswith(".gz") else raw
    if read(archive) != read(run):
        sys.exit(f"Archive differs: {name}")
    print(f"Verified {name}")
PY
