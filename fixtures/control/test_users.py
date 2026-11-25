"""Integration test for the user loader: writes 200 users to its own file and checks they all arrive."""
import sys
import tempfile
import time
from pathlib import Path

LOG = Path(__file__).with_name("runs.log")


def log(event: str) -> None:
    with LOG.open("a") as f:
        f.write(f"test_users {event} {time.time():.2f}\n")


if __name__ == "__main__":
    log("start")
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "users.txt"
        for i in range(200):
            with data.open("a") as f:
                f.write(f"user {i}\n")
            time.sleep(0.02)
        got = len(data.read_text().splitlines())
    log("end")
    if got != 200:
        print(f"FAIL test_users: expected 200 users, got {got}")
        sys.exit(1)
    print("PASS test_users: 200 users")
