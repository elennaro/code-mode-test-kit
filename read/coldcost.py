"""What each session would cost with a cold start: the cache read of its first request priced as a cache write.

Usage: python coldcost.py FOLDER...   prints run, first-request cache read, extra US dollars
Waiting more than 5 minutes does not make a start cold: 5 minutes is the cache's minimum lifetime, so a
prefix can still be there much later. Adding this extra to runs.py's usd puts every run on a cold start.
The write is priced at the 1-hour rate when the session wrote 1-hour cache (a subscription), else the 5-minute rate.
"""
import glob
import json
import sys

from logs import folders, label

BASE, READ, WRITE_5M, WRITE_1H = 4.0, 0.05, 1.25, 2.0  # the same prices as runs.py


def extra(path: str) -> tuple[int, float]:
    first, one_hour = None, False
    for line in open(path, encoding="utf-8"):
        try:
            row = json.loads(line)
        except ValueError:
            continue
        msg = row.get("message") or {}
        u = msg.get("usage")
        if row.get("type") != "assistant" or row.get("isSidechain") or not u or msg.get("model") == "<synthetic>":
            continue
        one_hour = one_hour or (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) > 0
        first = u.get("cache_read_input_tokens", 0) if first is None else first
    read = first or 0
    return read, read * ((WRITE_1H if one_hour else WRITE_5M) - READ) * BASE / 1e6


if __name__ == "__main__":
    for folder in folders(sys.argv[1:]):
        for path in sorted(glob.glob(folder + "/*.jsonl")):
            read, usd = extra(path)
            print(label(folder), read, f"{usd:.4f}", sep="\t")
