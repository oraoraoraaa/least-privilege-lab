"""Exercise both routes with explicit predictions and count actual native calls."""

from unittest.mock import patch

from fresh import predicted_fields, schema_only, snapshot

SPEC = {"unsupported": None, "migration_schema": False}
files = {
    "items.sq": """CREATE TABLE item(id INTEGER, title TEXT, visible INTEGER);
CREATE VIEW titles AS SELECT title FROM item;
viewRead:
SELECT title FROM titles;
directRead:
SELECT * FROM item;
"""
}
old_db = schema_only(files, SPEC)
old, errors = snapshot(files, old_db)
assert not errors
# The new SQL in the file is unavailable to the predictor apart from its DDL.
changed = {
    "items.sq": files["items.sq"]
    .replace("title FROM item;", "title FROM item WHERE visible;")
    .replace("SELECT * FROM item;", "SELECT id FROM item;")
}
plan = schema_only(changed, SPEC)
with patch.object(plan, "execute", wraps=plan.execute) as calls:
    rows = predicted_fields(old, plan, ("selective",))
    assert calls.call_count == 1
assert rows["items.viewRead"]["selective"]["added"] == ["item.visible"]
assert rows["items.directRead"]["selective"]["route"] == "source"
removed = schema_only(
    {"items.sq": "CREATE TABLE item(id INTEGER, title TEXT, visible INTEGER);"}, SPEC
)
row = predicted_fields(old, removed, ("selective",))["items.viewRead"]["selective"]
assert row["route"] == "rehearsal" and row["error"] and row["added"] == []
for db in (old_db, plan, removed):
    db.db.close()
print("Verified both selective routes, including omitted and changed views.")
