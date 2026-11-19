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
UPSTREAM = "https://raw.githubusercontent.com/chrisbanes/tivi/"
HEAD = "a0c62c2c763c83e3a0ecf79b283224374bb06c4a"
CUTOFFS = ("2023-06-30","2023-09-30","2023-12-31","2024-03-31","2024-06-30","2024-09-30","2024-11-12")


def make_manifest(repo):
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args])
    snapshots = []
    for date in CUTOFFS:
        rev = git("rev-list","--first-parent","-1","--before="+date+"T23:59:59Z",HEAD).decode().strip()
        files = {}
        for row in git("ls-tree","-r",rev).decode().splitlines():
            entry, path = row.split("\t")
            if path.endswith(".sq") and "/src/commonMain/sqldelight/" in path:
                files[path] = hashlib.sha256(git("cat-file","blob",entry.split()[2])).hexdigest()
        if not files:
            raise ValueError(date)
        snapshots.append({"cutoff":date, "revision":rev, "files":files})
    return snapshots


def load_sources(cache):
    manifest = json.loads((HERE/"sources.json").read_text())
    unique = {}
    for snapshot in manifest:
        for path, digest in snapshot["files"].items():
            unique.setdefault(digest, UPSTREAM + snapshot["revision"] + "/" + quote(path))
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
    print(json.dumps(make_manifest(parser.parse_args().repository),indent=2,sort_keys=True))
