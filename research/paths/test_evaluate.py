import itertools
from collections import Counter
from math import comb
from statistics import mean
import unittest

from evaluate import deploy, matched, rankings


class EvaluationTests(unittest.TestCase):
    def test_matched_prefix_against_all_orderings(self):
        # The fourth required label is sometimes outside the candidate universe.
        for tiers in [[{"a","b","c"},{"d","e"}], [set(), {"a","b"}, {"c","d","e"}]]:
            for n in range(4):
                for needed in itertools.combinations("abcdeX",n):
                    missing = set(needed)
                    excess = len(set.union(*tiers)-missing)
                    for allowance in range(excess+1):
                        retained, success = [], []
                        permutations = [list(itertools.permutations(t)) for t in tiers]
                        for blocks in itertools.product(*permutations):
                            grants = set()
                            for item in itertools.chain.from_iterable(blocks):
                                if item not in missing and len(grants-missing) == allowance:
                                    break
                                grants.add(item)
                            self.assertEqual(len(grants-missing), allowance)
                            retained.append(len(grants & missing))
                            success.append(missing <= grants)
                        actual = matched(tiers, missing, allowance)
                        self.assertAlmostEqual(actual[0],mean(retained))
                        self.assertAlmostEqual(actual[1],mean(success))

    def test_rankings_cover_domain_and_placebo_matches_table_sizes(self):
        universe = {"a.x","a.y","a.z","b.u","b.v","c.w"}
        o, d = {"a.x"}, {"a.x","a.z","b.v"}
        groups = rankings(universe,o,d,Counter(),"visible-pair")
        for tiers in groups.values():
            self.assertEqual(set().union(*tiers),universe-o)
            self.assertEqual(sum(map(len,tiers)),len(universe-o))
            self.assertTrue(o <= deploy(tiers,o,2) <= universe)
        counts = lambda pool: Counter(x.split(".")[0] for x in pool-o)
        self.assertEqual(counts(deploy(groups["placebo"],o,len(d-o))),counts(d))
        self.assertEqual(deploy(groups["sibling"],o,len(d-o)),o|d)


if __name__ == "__main__":
    unittest.main()
