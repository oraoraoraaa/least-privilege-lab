import unittest

from review import load_snapshot, migration_report, Instrument, schema_sql


class MigrationReviewTests(unittest.TestCase):
    def test_old_source_and_new_ddl_are_sufficient(self):
        old = {"catalog.sq":"""CREATE TABLE title(id INTEGER, label TEXT);
get:
SELECT * FROM title WHERE id=:id;
keep:
SELECT label FROM title;
"""}
        future = {"catalog.sq":"""CREATE TABLE title(id INTEGER, label TEXT, notes TEXT);
get:
deliberately invalid future query;
"""}
        previous = load_snapshot(old)
        next_db = Instrument(schema_sql(future),include_views=True)
        report = migration_report(previous,next_db)
        self.assertEqual(report["old_named_reads"],2)
        self.assertEqual(report["alerts"],{"catalog.get":{"reason":"expanded_reads","added_reads":["title.notes"]}})
        # A changed future query can ask for an existing grant without a schema signal.
        allowed, _ = next_db.execute("SELECT id FROM title", previous.reads["catalog.keep"])
        self.assertFalse(allowed)
        next_db.db.close()
        previous.db.db.close()

    def test_removed_column_supplies_a_preparation_error(self):
        old = load_snapshot({"report.sq":"CREATE TABLE t(id INTEGER, detail TEXT);\nget:\nSELECT detail FROM t;"})
        planned = Instrument("CREATE TABLE t(id INTEGER);",include_views=True)
        flag = migration_report(old,planned)["alerts"]["report.get"]
        self.assertEqual(flag["reason"],"prepare_failed")
        self.assertIn("detail",flag["error"])
        old.db.db.close()
        planned.db.close()


if __name__ == "__main__":
    unittest.main()
