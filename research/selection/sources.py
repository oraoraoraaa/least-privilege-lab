"""Pin and retrieve only the application's published SQLDelight source files."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
UPSTREAM = "https://raw.githubusercontent.com/"
HEAD = "a0c62c2c763c83e3a0ecf79b283224374bb06c4a"
CUTOFFS = ("2023-06-30","2023-09-30","2023-12-31","2024-03-31","2024-06-30","2024-09-30","2024-11-12")


MIHON_REVISIONS = (
    "a605a4ec7572919f8c6ad599dce677dd648ca2ad","38d5fc91606f28287827bc53ee1410d8ab54bf9f",
    "6294521460a8eb8b755b7a8c3c07d4bfa2e9a9e0","e4de208cf75e273b425bf4b1fe4bd7bc3d9cc459",
    "19f1d00fcbef6ab7783066ff9ae8e377f696b231","79fc3a0a8aaa6cd2b6dc21c3f8ee53f008da654a")


def make_manifest(repo, series):
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args])
    fragment = "/src/commonMain/sqldelight/"
    if series == "quarterly":
        schedule = [(date, git("rev-list","--first-parent","-1","--before="+date+"T23:59:59Z",
                              HEAD).decode().strip()) for date in CUTOFFS]
    elif series == "events":
        initial = "2eaefa1ff0d0290320fcef43b09c5f031d1fbba3"
        revisions = git("log","--first-parent","--diff-merges=first-parent","--reverse","--format=%H",
                        initial+".."+HEAD,"--",":(glob)**/src/commonMain/sqldelight/**/*.sq").decode().splitlines()
        schedule = [(git("show","-s","--format=%cs",rev).decode().strip(),rev) for rev in [initial,*revisions,HEAD]]
    else:
        schedule = [(f"v0.{i}.0", rev) for i,rev in enumerate(MIHON_REVISIONS,16)]
        fragment = "/src/main/sqldelight/"
    snapshots = []
    for label, rev in schedule:
        files = {}
        for row in git("ls-tree","-r",rev).decode().splitlines():
            entry, path = row.split("\t")
            if path.endswith(".sq") and fragment in path:
                files[path] = hashlib.sha256(git("cat-file","blob",entry.split()[2])).hexdigest()
        if not files:
            raise ValueError(label)
        if series != "events" or not snapshots or snapshots[-1]["files"] != files:
            snapshots.append({"cutoff":label, "revision":rev, "files":files})
    return snapshots


def load_sources(cache, manifest_name="sources.json", upstream="chrisbanes/tivi"):
    manifest = json.loads((HERE/manifest_name).read_text())
    unique = {}
    for snapshot in manifest:
        for path, digest in snapshot["files"].items():
            unique.setdefault(digest, UPSTREAM + upstream + "/" + snapshot["revision"] + "/" + quote(path))
    cache.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        digest, url = item
        target = cache/digest
        if target.exists():
            data = target.read_bytes()
        else:
            with urlopen(url, timeout=45) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Source digest mismatch for {url}")
        if not target.exists():
            with NamedTemporaryFile(dir=cache,delete=False) as tmp:
                tmp.write(data)
            Path(tmp.name).replace(target)
        return digest, data.decode()

    with ThreadPoolExecutor(max_workers=6) as pool:
        blobs = dict(pool.map(fetch, unique.items()))
    return [(s, {p:blobs[d] for p,d in s["files"].items()}) for s in manifest]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rebuild the source manifest from a complete upstream Git history.")
    parser.add_argument("repository", type=Path)
    parser.add_argument("--series", choices=("quarterly","events","mihon"),default="quarterly")
    args = parser.parse_args()
    print(json.dumps(make_manifest(args.repository,args.series),indent=2,sort_keys=True))
