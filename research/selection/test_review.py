import unittest

from column_coverage import coverage_alerts
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

    def test_column_coverage_uses_all_prior_fields_and_detects_removals(self):
        old = {"book.@row", "book.id", "book.title", "view.title", "tag.label"}
        planned = (old - {"tag.label"}) | {"book.notes", "view.notes", "new.title"}
        reads = {"all_columns": {"book.id", "book.title"}, "some_columns": {"book.title"},
                 "count_only": {"book.@row"}, "read_view": {"view.title"},
                 "removed": {"tag.label"}, "constant": set()}
        alerts = coverage_alerts(old, planned, reads)
        self.assertEqual(set(alerts), {"all_columns", "read_view", "removed"})
        self.assertEqual(alerts["read_view"]["growing_full_relations"], ["view"])
        self.assertEqual(alerts["removed"]["removed_reads"], ["tag.label"])

    def test_identical_old_read_sets_diverge_after_a_column_addition(self):
        previous = load_snapshot({"t.sq": "CREATE TABLE t(id INTEGER, title TEXT);\n"
                                  "star:\nSELECT * FROM t;\nlist:\nSELECT id, title FROM t;"})
        planned = Instrument("CREATE TABLE t(id INTEGER, title TEXT, notes TEXT);", include_views=True)
        try:
            self.assertEqual(previous.reads["t.star"], previous.reads["t.list"])
            alerts = coverage_alerts(previous.db.universe, planned.universe, previous.reads)
            self.assertEqual(set(alerts), {"t.star", "t.list"})
            report = migration_report(previous, planned)
            self.assertEqual(report["alerts"], {"t.star": {"reason": "expanded_reads",
                                                          "added_reads": ["t.notes"]}})
        finally:
            planned.db.close()
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
