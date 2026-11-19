#!/bin/sh
# Run from anywhere in the checkout. An optional argument points at an existing upstream Git repository.
set -eu
root=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$root"
mkdir -p build
scratch=$(mktemp -d "$root/build/classroom-check.XXXXXX")
trap 'rm -rf "$scratch"' EXIT
if [ "$#" -gt 1 ]; then
    echo 'usage: sh research/classroom/reproduce.sh [RESTRICTER_GIT_CHECKOUT]' >&2
    exit 2
fi
artifact=$root/build/restricter
if [ "$#" -eq 1 ]; then
    artifact=$1
elif ! git -C "$artifact" cat-file -e '35331c1259d1c04f4f453aab60e9f3f338d9d544^{commit}' 2>/dev/null; then
    artifact=$scratch/upstream.git
    git init -q --bare "$artifact"
    git -C "$artifact" fetch -q --depth=1 https://github.com/REASONERSLab/Restricter.git \
        35331c1259d1c04f4f453aab60e9f3f338d9d544
fi
make -s test
uv run --locked --script research/classroom/replay.py --artifact "$artifact" --output "$scratch/results"
diff -ru research/classroom/results "$scratch/results"
uv run --no-project --python 3.12 python -B research/classroom/test_exact_retention.py
uv run --no-project --python 3.12 python -B research/classroom/exact_retention.py "$scratch/results" > "$scratch/exact.json"
diff -u research/classroom/exact-retention.json "$scratch/exact.json"
echo 'Verified all archived classroom results.'
