"""Old-catalog predictors shared by the migration experiment and the CLI."""
from collections import defaultdict
from functools import lru_cache

from sqlglot import exp, parse_one
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.scope import Scope, traverse_scope

from application import added_on_touched_relations, preview_query
from column_coverage import coverage_alerts


class UnresolvedProjection(ValueError):
    pass


@lru_cache(maxsize=8192)
def wildcard_relations(sql, views):
    """Resolve projection stars in old SQL, including stars inside referenced views."""
    definitions = dict(views)
    relations = set()

    def visit(statement, ancestors):
        tree = parse_one(statement, read="sqlite")
        if isinstance(tree, exp.Create):
            tree = tree.expression
        if not isinstance(tree, exp.Query):
            raise UnresolvedProjection("unsupported query shape")
        for scope in traverse_scope(tree):
            sources = {name.lower(): source for name, (_, source) in scope.selected_sources.items()}
            for source in sources.values():
                if isinstance(source, exp.Table) and source.name.lower() in definitions:
                    name = source.name.lower()
                    if name in ancestors:
                        raise UnresolvedProjection("recursive view")
                    visit(definitions[name], ancestors | {name})
            for item in scope.expression.selects:
                if not (isinstance(item, exp.Star) or isinstance(item, exp.Column) and item.is_star):
                    continue
                qualifier = item.table.lower() if isinstance(item, exp.Column) else ""
                if qualifier and qualifier not in sources:
                    raise UnresolvedProjection("unresolved wildcard qualifier")
                selected = [sources[qualifier]] if qualifier else sources.values()
                for source in selected:
                    if isinstance(source, Scope):
                        # Its inner SELECT was visited in its own scope.
                        continue
                    if not isinstance(source, exp.Table) or not isinstance(source.this, exp.Identifier):
                        raise UnresolvedProjection("unresolved wildcard source")
                    relations.add(source.name.lower())
    visit(sql, set())
    return frozenset(relations)


def predicted_fields(old, planned, methods=("diff", "coverage", "source", "rehearsal")):
    before, after = old.db.universe, planned.universe
    additions = defaultdict(set)
    for field in after - before:
        relation, col = field.rsplit(".", 1)
        if col != "@row":
            additions[relation].add(field)
    covered = coverage_alerts(before, after, old.reads)
    predictions = {}
    views = tuple(sorted(old.db.view_definitions.items()))
    for name, query in sorted(old.queries.items()):
        observed = old.reads[name]
        removed = sorted(observed - after)
        row = {}
        for method in methods:
            error = None
            if method == "diff":
                added = added_on_touched_relations(observed, before, after)
            elif method == "coverage":
                full = covered.get(name, {}).get("growing_full_relations", [])
                added = {field for rel in full for field in additions[rel]}
            elif method == "source":
                try:
                    stars = wildcard_relations(query.sql, views)
                    added = {field for rel in stars for field in additions[rel]}
                except (SqlglotError, UnresolvedProjection) as exc:
                    error = "abstain: " + str(exc).splitlines()[0]
                    added = set()
            elif method == "rehearsal":
                reads, error = preview_query(planned, query)
                added = reads - observed
            else:
                raise ValueError(method)
            row[method] = {"added": sorted(added), "removed": removed, "error": error,
                           "flag": bool(added or error or (removed and method != "rehearsal"))}
        predictions[name] = row
    return predictions
