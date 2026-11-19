"""Verify one point lookup in two published Mihon release packages."""
from hashlib import sha256
import io
import re
import struct
import zipfile

from workloads import checked_file

DIGESTS = {"v0.18.0":"24935b7af6a868639705e95c978dcd8c7ab734e2de40f45f0ca906d752f51021",
           "v0.19.0":"0cebd3b5cacf9b828a312da3e2bc209968e18cb7da5605d0f2f1aaf21462dc63"}
QUERY = "mangas.getMangaById"
LOOKUP = re.compile(r"select\s+(.+?)\s+from\s+mangas\s+where\s+(?:mangas\.)?_id\s*=\s*\?(?:1)?\s*;?",re.I|re.S)


def projection_of(sql):
    normalized = sql.strip().replace(chr(96),"").replace('"',"")
    match = LOOKUP.fullmatch(normalized)
    return match[1].strip() if match else None


def lookups(package):
    literals = set()
    with zipfile.ZipFile(io.BytesIO(package)) as apk:
        for name in apk.namelist():
            if not re.fullmatch(r"classes\d*\.dex",name):
                continue
            data = apk.read(name)
            if not data.startswith(b"dex\n") or data[40:44] != b"\x78\x56\x34\x12":
                raise ValueError(f"Unsupported DEX header in {name}")
            count,start = struct.unpack_from("<II",data,56)
            for offset, in struct.iter_unpack("<I", data[start:start+4*count]):
                while data[offset] & 128:  # DEX string length in ULEB128 form.
                    offset += 1
                begin = offset+1
                if data[begin:begin+6].lower() != b"select":
                    continue
                raw = data[begin:data.index(b"\0",begin)]
                if raw.isascii():
                    sql = raw.decode()
                    if projection_of(sql):
                        literals.add(sql)
    return sorted(literals)


def verify(cache, apps):
    cache.mkdir(parents=True,exist_ok=True)
    result = {}
    old_sql = None
    for tag,digest in DIGESTS.items():
        url = f"https://github.com/mihonapp/mihon/releases/download/{tag}/mihon-x86_64-{tag}.apk"
        raw = checked_file(cache,tag+".apk",url,digest)
        app = apps[tag]
        expected = app.reads[QUERY]
        candidates = []
        for sql in lookups(raw):
            projection = projection_of(sql).lower()
            columns = {c.strip().removeprefix("mangas.") for c in projection.split(",")}
            if projection in ("*","mangas.*") or {"mangas."+c for c in columns} == expected:
                candidates.append(sql)
        row = {"url":url,"package_sha256":digest,"matching_literals":len(candidates)}
        if len(candidates) == 1:
            sql = candidates[0]
            ok,fp = app.db.execute(sql,bindings=(1,))
            row.update(literal_sha256=sha256(sql.encode()).hexdigest(),projection=projection_of(sql),
                       own_schema_reads=sorted(fp),agrees_with_source=ok and fp==expected)
            if old_sql is not None:
                _,old_on_new = app.db.execute(old_sql,bindings=(1,))
                row["old_literal_on_new_schema"] = sorted(old_on_new)
                row["new_literal_adds_over_old_literal_on_new_schema"] = sorted(fp-old_on_new)
            old_sql = sql
        result[tag] = row
    return result
