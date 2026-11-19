"""Compare policies as finite grant sets and as symbolic request predicates."""
import z3


def grants(rules):
    return {(r.principal, r.action, resource) for r in rules for resource in r.resources}


def verify(original, candidate, required):
    before, after = grants(original), grants(candidate)
    principal, action, resource = z3.Strings("principal action resource")

    def permits(rules):
        return z3.Or([z3.And(principal == rule.principal, action == rule.action,
                             z3.Or([resource == value for value in rule.resources]))
                      for rule in rules])

    required_predicate = z3.Or([z3.And(principal == p, action == a, resource == r)
                                for p, a, r in required])
    allowed = permits(candidate)
    properties = [
        ("new_grant", after - before, z3.And(allowed, z3.Not(permits(original)))),
        ("lost_requirement", required - after, z3.And(required_predicate, z3.Not(allowed))),
    ]
    checks = {}
    for name, violations, formula in properties:
        solver = z3.Solver()
        solver.set(timeout=5000)
        solver.add(formula)
        result = solver.check()
        if result == z3.unknown:
            raise ValueError(f"Unverified {name}: {solver.reason_unknown()}")
        if (result == z3.sat) != bool(violations):
            raise ValueError(f"Enumeration and Z3 disagree on {name}")
        if result == z3.sat:
            model = solver.model()
            witness = tuple(model.eval(x, model_completion=True).as_string()
                            for x in (principal, action, resource))
            if witness not in violations:
                raise ValueError(f"Invalid symbolic witness for {name}: {witness}")
        checks[name] = {"smt": str(result), "count": len(violations),
                        "first_witness": min(violations) if violations else None}
    return {"original_grants": len(before), "candidate_grants": len(after),
            "removed_grants": len(before - after), "requirements": len(required),
            "checks": checks, "accepted": after <= before and required <= after}
