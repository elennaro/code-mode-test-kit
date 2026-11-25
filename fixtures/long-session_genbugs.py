"""Make a small Python package with 12 one-line bugs and unittest tests, for the long-session test.

Usage: python long-session_genbugs.py <folder>
"""

import sys
from pathlib import Path

# name: (buggy source, test body)
MODULES = {
    "slug": (
        "def slugify(text):\n    return text.strip().replace(' ', '-')\n",
        "self.assertEqual(m.slugify(' Hello World '), 'hello-world')\n"
        "        self.assertEqual(m.slugify('A B'), 'a-b')",
    ),
    "average": (
        "def average(xs):\n    return sum(xs) / (len(xs) - 1)\n",
        "self.assertEqual(m.average([2, 4, 6]), 4)\n        self.assertEqual(m.average([5]), 5)",
    ),
    "clamp": (
        "def clamp(x, lo, hi):\n    return max(hi, min(lo, x))\n",
        "self.assertEqual(m.clamp(5, 0, 10), 5)\n"
        "        self.assertEqual(m.clamp(-3, 0, 10), 0)\n"
        "        self.assertEqual(m.clamp(42, 0, 10), 10)",
    ),
    "leap": (
        "def is_leap(year):\n    return year % 4 == 0 and year % 100 != 0\n",
        "self.assertTrue(m.is_leap(2024))\n"
        "        self.assertFalse(m.is_leap(1900))\n"
        "        self.assertTrue(m.is_leap(2000))",
    ),
    "words": (
        "def word_count(text):\n    return len(text.split(' '))\n",
        "self.assertEqual(m.word_count('one two'), 2)\n"
        "        self.assertEqual(m.word_count('  one   two  '), 2)\n"
        "        self.assertEqual(m.word_count(''), 0)",
    ),
    "fizz": (
        "def fizz(n):\n"
        "    if n % 3 == 0:\n        return 'Fizz'\n"
        "    if n % 5 == 0:\n        return 'Buzz'\n"
        "    if n % 15 == 0:\n        return 'FizzBuzz'\n"
        "    return str(n)\n",
        "self.assertEqual(m.fizz(15), 'FizzBuzz')\n"
        "        self.assertEqual(m.fizz(9), 'Fizz')\n"
        "        self.assertEqual(m.fizz(10), 'Buzz')\n"
        "        self.assertEqual(m.fizz(7), '7')",
    ),
    "reverse": (
        "def reverse_words(text):\n    return text[::-1]\n",
        "self.assertEqual(m.reverse_words('red green blue'), 'blue green red')",
    ),
    "median": (
        "def median(xs):\n    mid = len(xs) // 2\n"
        "    if len(xs) % 2:\n        return xs[mid]\n"
        "    return (xs[mid - 1] + xs[mid]) / 2\n",
        "self.assertEqual(m.median([3, 1, 2]), 2)\n        self.assertEqual(m.median([4, 1, 3, 2]), 2.5)",
    ),
    "celsius": (
        "def to_celsius(f):\n    return (f - 32) * 9 / 5\n",
        "self.assertAlmostEqual(m.to_celsius(212), 100)\n        self.assertAlmostEqual(m.to_celsius(32), 0)",
    ),
    "tail": (
        "def last_n(xs, n):\n    return xs[-n:]\n",
        "self.assertEqual(m.last_n([1, 2, 3], 2), [2, 3])\n        self.assertEqual(m.last_n([1, 2, 3], 0), [])",
    ),
    "merge": (
        "def merge(a, b):\n    out = dict(b)\n    out.update(a)\n    return out\n",
        "self.assertEqual(m.merge({'x': 1, 'y': 1}, {'y': 2}), {'x': 1, 'y': 2})",
    ),
    "chunk": (
        "def chunk(xs, size):\n    return [xs[i:i + size] for i in range(0, len(xs) - size, size)]\n",
        "self.assertEqual(m.chunk([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]])\n"
        "        self.assertEqual(m.chunk([1, 2], 2), [[1, 2]])",
    ),
}


def main(folder: str) -> None:
    root = Path(folder)
    pkg, tests = root / "tools", root / "tests"
    pkg.mkdir(parents=True, exist_ok=True)
    tests.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (tests / "__init__.py").write_text("")
    (root / "pytest.ini").write_text("[pytest]\n")  # isolate the fixture from any inherited pytest configuration
    for name, (src, body) in MODULES.items():
        (pkg / f"{name}.py").write_text(src)
        (tests / f"test_{name}.py").write_text(
            f"import unittest\n\nfrom tools import {name} as m\n\n\n"
            f"class Test{name.title()}(unittest.TestCase):\n"
            f"    def test_{name}(self):\n        {body}\n\n\n"
            "if __name__ == '__main__':\n    unittest.main()\n"
        )


if __name__ == "__main__":
    main(sys.argv[1])
