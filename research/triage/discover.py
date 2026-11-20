"""Rediscover the three prospective cohorts without reading query outcomes."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1, sha256
from pathlib import Path
from subprocess import check_output, run
from urllib.parse import quote
from urllib.request import urlopen
import json
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = ROOT / "build/triage"
PROJECTS = {
    "ACINQ/phoenix": ("f3a227624c2ab262351a5261a5e4a1c6bdfc4887", "phoenix-shared", ["appdb", "channelsdb", "paymentsdb"]),
    "saket/press": ("5f64350ec51402f3e6aeff145cbc35438780a03c", "shared", [""]),
    "cashapp/zipline": ("9bc5139c4b86ecf65b7be12242745f69bee83128", "zipline-loader", [""]),
}


def download(url):
    for attempt in range(4):
        try:
            with urlopen(url, timeout=45) as response:
                return response.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def raw(project, rev, path):
    return download(f"https://raw.githubusercontent.com/{project}/{rev}/{quote(path)}")


def fetch(project, record):
    digest, (rev, path) = record
    dest = CACHE / "inputs" / digest
    data = dest.read_bytes() if dest.exists() else raw(project, rev, path)
    if sha256(data).hexdigest() != digest:
        raise ValueError(f"Input mismatch in {project} {rev} {path}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        dest.write_bytes(data)
    return digest, data.decode("utf-8-sig")


def discover(project):
    head, module, names = PROJECTS[project]
    repo = CACHE / (project.split("/")[1] + ".git")
    CACHE.mkdir(parents=True, exist_ok=True)
    if not repo.exists():
        run(["git", "clone", "--bare", "--filter=blob:none", "--no-tags",
             f"https://github.com/{project}.git", str(repo)], check=True)

    def git(*args):
        return check_output(["git", "--git-dir", str(repo), *args]).decode().splitlines()

    by_db, objects = {}, {}
    for name in names:
        prefix = module + "/src/commonMain/sqldelight/" + (name + "/" if name else "")
        revisions = git("log", "--first-parent", "--diff-merges=first-parent", "--no-renames",
                        "--reverse", "--no-patch", "--format=%H", head, "--", prefix)
        steps = []
        previous = {}
        for rev in revisions:
            files = {}
            config = {}
            for entry in git("ls-tree", "-r", rev, "--", prefix, module+"/build.gradle", module+"/build.gradle.kts"):
                meta, path = entry.split("\t", 1)
                oid = meta.split()[2]
                if path.endswith((".sq", ".sqm")):
                    files[path] = oid
                elif "/build.gradle" in path:
                    config[path] = oid
                else:
                    continue
                objects.setdefault(oid, (rev, path))
            if files != previous:
                steps.append(dict(revision=rev, files=files, config=config))
            previous = files
        by_db[name or module] = steps

    def retrieve(item):
        oid, (rev, path) = item
        cache = CACHE / "objects" / oid
        data = cache.read_bytes() if cache.exists() else raw(project, rev, path)
        if sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != oid:
            raise ValueError(path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(data)
        digest = sha256(data).hexdigest()
        dest = CACHE / "inputs" / digest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return oid, digest

    with ThreadPoolExecutor(10) as pool:
        lookup = dict(pool.map(retrieve, sorted(objects.items())))
    provenance = {}
    for steps in by_db.values():
        for step in steps:
            for key in ("config", "files"):
                for path, oid in step[key].items():
                    digest = lookup[oid]
                    step[key][path] = digest
                    provenance.setdefault(digest, objects[oid])
    print(project, {k:len(v) for k,v in by_db.items()}, flush=True)
    return project, dict(head=head, databases=by_db, inputs=provenance)


if __name__ == "__main__":
    with ThreadPoolExecutor(3) as pool:
        out = dict(pool.map(discover, PROJECTS))
    Path(sys.argv[1]).write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
