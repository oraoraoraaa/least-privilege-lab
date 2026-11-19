#!/bin/sh
set -eu
jar=$1
case_dir=examples/registry
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

review() {
    java -jar "$jar" review "$@"
}

review "$case_dir/grants.tsv" "$case_dir/events.tsv" > "$tmp/report"
diff -u "$case_dir/expected.tsv" "$tmp/report"

# Duplicate grants denote a set. Event multiplicity still matters.
cp "$case_dir/grants.tsv" "$tmp/grants"
tail -n 1 "$case_dir/grants.tsv" >> "$tmp/grants"
review "$tmp/grants" "$case_dir/events.tsv" > "$tmp/report"
diff -u "$case_dir/expected.tsv" "$tmp/report"

# Reject a malformed trailing decision before emitting a partial report.
cp "$case_dir/events.tsv" "$tmp/events"
printf '2026-10-06T00:00:00Z\tinference\tread\tmodel:stable\tMAYBE\n' >> "$tmp/events"
if review "$case_dir/grants.tsv" "$tmp/events" > "$tmp/report" 2> "$tmp/error"; then
    exit 1
fi
test ! -s "$tmp/report"
grep -Fq ':9: expected ALLOW or DENY' "$tmp/error"
echo 'Review checks passed.'
