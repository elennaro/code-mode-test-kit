"""Test fixtures: a small data file that each integration test fills and reads back."""
import time
from pathlib import Path

DATA = Path(__file__).with_name(".fixture_data.txt")
LOG = Path(__file__).with_name("runs.log")


def log(name: str, event: str) -> None:
    with LOG.open("a") as f:
        f.write(f"{name} {event} {time.time():.2f}\n")


def fill(rows: int) -> None:
    DATA.write_text("")
    for i in range(rows):
        with DATA.open("a") as f:
            f.write(f"row {i}\n")
        time.sleep(0.02)


def count() -> int:
    return len(DATA.read_text().splitlines()) if DATA.exists() else 0


def clean() -> None:
    DATA.unlink(missing_ok=True)
