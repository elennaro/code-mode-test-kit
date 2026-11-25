"""Integration test for the order loader: writes 150 orders to its own file and checks they all arrive."""
import sys
import tempfile
import time
from pathlib import Path

LOG = Path(__file__).with_name("runs.log")


def log(event: str) -> None:
    with LOG.open("a") as f:
        f.write(f"test_orders {event} {time.time():.2f}\n")


if __name__ == "__main__":
    log("start")
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "orders.txt"
        for i in range(150):
            with data.open("a") as f:
                f.write(f"order {i}\n")
            time.sleep(0.02)
        got = len(data.read_text().splitlines())
    log("end")
    if got != 150:
        print(f"FAIL test_orders: expected 150 orders, got {got}")
        sys.exit(1)
    print("PASS test_orders: 150 orders")
