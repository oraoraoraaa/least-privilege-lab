"""Rebuild the pinned first-parent manifest; only source and configuration are inspected here."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import quote
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
CACHE = HERE.parents[1] / "build/migration-inputs"
PROTOCOL = "a5ebb6bba5729c6250179d7b82b9bdcdda012d6f"
PROJECTS = dict(re.findall(r"\| ([\w-]+/[\w-]+) \| ([a-f0-9]{40}) \|",
                           (HERE / "PROTOCOL.md").read_text()))


def dump(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as out:
        out.write(data)


def block(text, start):
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError("Unbalanced Gradle database block")


def declarations(config):
    match = re.search(r"(?m)^\s*sqldelight\s*\{", config)
    if not match:
        return []
    body = block(config, match.end()-1)
    result = []
    for m in re.finditer(r'(?:create|register|database)\s*\(\s*"(\w+)"\s*\)\s*\{', body):
        contents = block(body, m.end()-1)
        dirs = sorted(set(re.findall(r'(sqldelight\w*)["/]', line, re.I)[-1]
                          for line in contents.splitlines() if "srcDirs" in line and
                          re.findall(r'(sqldelight\w*)["/]', line, re.I)))
        result.append({"name": m[1], "dirs": dirs or ["sqldelight"],
                       "dependencies": re.findall(r'dependency\(project\(":(.*?)"\)\)', contents),
                       "migrations": bool(re.search(r'deriveSchemaFromMigrations.*true', contents)),
                       "block": contents})
    return result


def module_for(path):
    if "/src/" not in path or not path.endswith((".sq", ".sqm")):
        return None
    module, suffix = path.split("/src/", 1)
    parts = suffix.split("/")
    if len(parts) < 3 or "test" in parts[0].lower():
        return None
    return module


def build_project(item):
    project, head = item
    repo = CACHE / (project.split("/")[1] + ".git")
    if not repo.exists():
        subprocess.run(["git", "clone", "--bare", "--filter=blob:none", "--no-tags",
                        "https://github.com/"+project+".git", str(repo)], check=True)

    def git(*args, data=None):
        return subprocess.check_output(["git","--git-dir="+str(repo),*args], input=data)
    def lines(*args):
        return git(*args).decode().splitlines()

    def before(date):
        rows = lines("rev-list","--first-parent","-1","--before="+date,head)
        return rows[0] if rows else None

    base = before("2022-12-31T23:59:59Z")
    end = before("2025-12-31T23:59:59Z")
    bounds = base+".."+end if base else end
    log = ["log","--first-parent","--diff-merges=first-parent","--no-renames"]
    sql = ["*.sq","*.sqm"]
    touched = lines(*log,"--format=","--name-only",bounds,"--",*sql)
    touched += lines("ls-tree","-r","--name-only",base or end)
    modules = sorted({m for p in touched if (m := module_for(p))})
    configs = [f"{m}/build.gradle{ext}" for m in modules for ext in ("",".kts")]
    revs = ([base] if base else []) + lines(*log,"--reverse","--no-patch","--format=%H",bounds,"--",*sql,*configs)
    objects, frames = {}, []
    for rev in revs:
        files = {}
        for entry in lines("ls-tree","-r",rev,"--",*modules):
            meta, path = entry.split("\t",1)
            if module_for(path) or path in configs:
                oid = meta.split()[2]
                objects.setdefault(oid, (rev,path))
                files[path] = oid
        frames.append((rev,files))
    def retrieve(oid):
        rev, path = objects[oid]
        target = CACHE / "git-blobs" / oid
        if target.exists():
            return oid, target.read_bytes()
        url = f"https://raw.githubusercontent.com/{project}/{rev}/{quote(path)}"
        for attempt in range(4):
            try:
                with urlopen(url, timeout=40) as response:
                    content = response.read()
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        header = f"blob {len(content)}".encode() + bytes(1)
        if hashlib.sha1(header+content).hexdigest() != oid:
            raise ValueError(f"Git blob mismatch for {url}")
        target.write_bytes(content)
        return oid, content

    (CACHE / "git-blobs").mkdir(parents=True, exist_ok=True)
    blobs, lookup, provenance = {}, {}, {}
    pool = CACHE / "blobs"
    pool.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as workers:
        contents = list(workers.map(retrieve, sorted(objects)))
    for oid, content in contents:
        digest = hashlib.sha256(content).hexdigest()
        (pool/digest).write_bytes(content)
        lookup[oid] = digest
        rev,path = objects[oid]
        provenance[digest] = [rev,path]
        if path in configs:
            blobs[oid] = content.decode()

    events = []
    previous = {}
    for rev,files in frames:
        dbs, modules_sql = {}, defaultdict(dict)
        for path, oid in files.items():
            if m := module_for(path):
                modules_sql[m][path] = lookup[oid]
        for module, sources in modules_sql.items():
            conf = next((p for p in configs if p.startswith(module+"/build.gradle") and p in files),None)
            cfg = blobs[files[conf]] if conf else ""
            declared = declarations(cfg)
            for spec in declared or [{"name":"unresolved", "dirs":[], "dependencies":[], "migrations":False, "block":""}]:
                own = {p:d for p,d in sources.items() if p.split("/src/")[1].split("/")[1] in spec["dirs"]}
                why = None
                if not declared:
                    why, own = "unresolved Gradle database declaration", sources
                for dep in spec["dependencies"]:
                    child = modules_sql.get(dep.replace(":","/"),{})
                    if not child:
                        why = "unresolved dependency " + dep
                    own.update(child)
                key = module+"/"+spec["name"]
                dbs[key] = {"files":own,"config":conf,"config_sha":lookup[files[conf]] if conf else None,
                            "block":spec["block"],"migration_schema":spec["migrations"],"unsupported":why}
            assigned = {p for key,db in dbs.items() if key.startswith(module+"/") for p in db["files"]}
            other = sources.keys()-assigned
            if other:
                dbs[module+"/unassigned"] = dict(files={p:sources[p] for p in other}, config=conf,
                    config_sha=lookup[files[conf]] if conf else None,block="",migration_schema=False,
                    unsupported="source directory outside resolved declaration")
        # Keep configuration evidence for the snapshot, suppress unrelated module build edits.
        signatures = {k:{p:x for p,x in row.items() if p!="config_sha"} for k,row in dbs.items()}
        if signatures != previous or not events:
            events.append({"revision":rev,"date":lines("show","-s","--format=%cI",rev)[0],"databases":dbs})
        previous = signatures
    used = {d for e in events for db in e["databases"].values() for d in [*db["files"].values(),db["config_sha"]] if d}
    print(project,len(events),"states",len(used),"blobs",flush=True)
    return project,dict(head=head,baseline=base,end=end,events=events,blobs={d:provenance[d] for d in used})


if __name__ == "__main__":
    CACHE.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        inventory = dict(pool.map(build_project,PROJECTS.items()))
    dump(Path(sys.argv[1]), {"protocol":PROTOCOL,"projects":inventory})
