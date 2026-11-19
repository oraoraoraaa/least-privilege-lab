"""Checks of source resolution, future-input separation, churn and native policy scope."""

from application import load_snapshot, schema_sql
from policy import assess, fit
from workloads import Instrument


def regressions():
    old = {
        "t.sq": """CREATE TABLE t(id INTEGER, title TEXT);
CREATE VIEW v AS SELECT x.* FROM t x;
a:
SELECT x.* FROM t AS x;
b:
SELECT id,title FROM t;
countRows:
SELECT COUNT(*) FROM t;
viewRead:
SELECT * FROM v;
retire:
SELECT title FROM t;
"""
    }
    future = {
        "t.sq": old["t.sq"]
        .replace("title TEXT", "title TEXT, notes TEXT, flag INTEGER")
        .replace("SELECT x.* FROM t x;", "SELECT id,notes FROM t;")
        .replace("SELECT id,title FROM t;", "SELECT notes FROM t;")
        .replace("retire:", "introduced:")
    }
    a = load_snapshot(old)
    plan = Instrument(schema_sql(future), include_views=True)
    preds, unit, shared = fit(a, plan)
    assert preds["t.a"]["source"]["added"] == ["t.flag", "t.notes"]
    assert (
        preds["t.b"]["source"]["added"] == preds["t.countRows"]["source"]["added"] == []
    )
    assert "t.notes" in preds["t.viewRead"]["source"]["added"]
    assert "t.notes" in preds["t.viewRead"]["rehearsal"]["added"]
    assert len(shared["coverage/1"] - shared["retain"]) == 1
    assert len(shared["coverage/all"] - shared["retain"]) < sum(
        len(x["coverage/all"] - x["retain"]) for x in unit.values()
    )
    other = Instrument(
        schema_sql(
            {
                "t.sq": future["t.sq"].replace(
                    "SELECT notes FROM t;", "SELECT flag FROM t;"
                )
            }
        ),
        include_views=True,
    )
    assert fit(a, other) == (preds, unit, shared)
    b = load_snapshot(future)
    scored = assess(a, b, (preds, unit, shared))
    assert scored["introduced"] == ["t.introduced"] and scored["retired"] == [
        "t.retire"
    ]
    assert not scored["rows"]["t.a"]["policies"]["rehearsal/all"]["denied"]
    a.queries["t.b"].sql = "SELECT unknown_alias.* FROM t"
    abstain = fit(a, plan)[0]["t.b"]["source"]
    assert abstain["flag"] and abstain["error"] and abstain["added"] == []
    same = load_snapshot(
        {"q.sq": "CREATE TABLE t(id INTEGER, x TEXT);\nq:\nSELECT id FROM t;"}
    )
    edit = load_snapshot(
        {"q.sq": "CREATE TABLE t(id INTEGER, x TEXT);\nq:\nSELECT x FROM t;"}
    )
    result = assess(same, edit, fit(same, edit.db))
    assert (
        result["rows"]["q.q"]["missing"] == ["t.x"]
        and not result["predictions"]["q.q"]["rehearsal"]["flag"]
    )
    for s in (a, b, same, edit):
        s.db.db.close()
    plan.db.close()
    other.db.close()
