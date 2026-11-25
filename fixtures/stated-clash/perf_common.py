"""Shared code for the two performance tests: busy work on every CPU core, timed against a budget."""
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

WORK = int(os.environ.get("PERF_WORK", "36000000"))
BUDGET_S = float(os.environ.get("PERF_BUDGET_S", "10"))


def _spin(n: int) -> int:
    total = 0
    for i in range(n):
        total += i * i % 7
    return total


def run(name: str) -> None:
    log = Path(__file__).with_name("runs.log")
    start = time.time()
    with log.open("a") as f:
        f.write(f"{name} start {start:.2f}\n")
    cores = os.cpu_count() or 1
    with Pool(cores) as pool:
        pool.map(_spin, [WORK] * cores * 2)
    end = time.time()
    with log.open("a") as f:
        f.write(f"{name} end {end:.2f}\n")
    took = end - start
    if BUDGET_S and took > BUDGET_S:
        print(f"FAIL {name}: {took:.1f} s, budget {BUDGET_S:.0f} s")
        sys.exit(1)
    print(f"PASS {name}: {took:.1f} s, budget {BUDGET_S:.0f} s")
