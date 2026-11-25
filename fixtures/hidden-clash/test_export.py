"""Integration test for the exporter: writes 150 rows and checks they can be read back."""
import sys

import fixtures

if __name__ == "__main__":
    fixtures.log("test_export", "start")
    fixtures.fill(150)
    got = fixtures.count()
    fixtures.clean()
    fixtures.log("test_export", "end")
    if got != 150:
        print(f"FAIL test_export: expected 150 rows, got {got}")
        sys.exit(1)
    print("PASS test_export: 150 rows")
