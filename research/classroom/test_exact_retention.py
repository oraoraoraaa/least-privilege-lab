import itertools
import unittest
from collections import Counter

from exact_retention import EDIT, POST, distribution


class ExactRetentionTest(unittest.TestCase):
    def test_against_direct_enumeration_of_distinguishable_rows(self):
        rows = [(POST, "x"), (POST, "x"), (POST, "y"), (EDIT, "x"), (EDIT, "x"), (EDIT, "z")]
        counts = [(action, copies) for (action, _), copies in Counter(rows).items()]
        for size in range(len(rows) + 1):
            expected = Counter()
            for sample in itertools.combinations(rows, size):
                distinct = Counter(action for action, _ in set(sample))
                expected[distinct[POST], distinct[EDIT]] += 1
            self.assertEqual(expected, distribution(counts, size))


if __name__ == "__main__":
    unittest.main()
