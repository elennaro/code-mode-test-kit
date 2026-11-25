"""Integration test for the importer: loads 200 rows and checks they all arrive."""
import sys

import fixtures

if __name__ == "__main__":
    fixtures.log("test_import", "start")
    fixtures.fill(200)
    got = fixtures.count()
    fixtures.clean()
    fixtures.log("test_import", "end")
    if got != 200:
        print(f"FAIL test_import: expected 200 rows, got {got}")
        sys.exit(1)
    print("PASS test_import: 200 rows")
