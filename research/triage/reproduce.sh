#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
run_python() {
  uv run --python 3.12 --with apsw==3.53.1.0 --with sqlglot==27.29.0 python -B "$@"
}
run_python research/triage/test_rule.py
uv run --locked --script research/triage/fresh.py "$scratch/fresh.json.gz"
run_python research/triage/audit.py "$scratch"
run_python research/triage/witnesses.py "$scratch/witnesses.json.gz"
run_python - research/triage/results "$scratch" <<'PY'
from pathlib import Path
import gzip
import sys
expected, actual = map(Path, sys.argv[1:])
files = {p.name for p in expected.glob("*.json.gz")}
assert files == {p.name for p in actual.iterdir()}
for name in sorted(files):
    if gzip.decompress((expected/name).read_bytes()) != gzip.decompress((actual/name).read_bytes()):
        raise SystemExit("Evidence differs: "+name)
    print("Verified",name)
PY
