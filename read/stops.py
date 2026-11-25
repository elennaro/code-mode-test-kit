"""One line per safety run: Claude Code version, Code Mode on or off, how many calls the deny rules, the auto
mode check and Claude Code's own checks stopped, and how many inner calls ran or failed.

Usage: python stops.py <log folder>...
Code Mode wraps calls in REPL. A REPL call counts only when the auto mode check stopped it (that check reads the
code before any inner call exists); otherwise only its inner calls are counted.
"""
import glob
import sys

from decoy import rows, verdict
from logs import folders, label

KEYS = {"denied": "rule", "auto check": "auto check", "asked": "own check", "ran": "ran", "failed": "failed"}

for folder in folders(sys.argv[1:]):
    calls, count, version = {}, dict.fromkeys(KEYS.values(), 0), set()
    for path in glob.glob(folder + "/*.jsonl"):
        for row, blocks in rows(path):
            if row.get("version"):
                version.add(row["version"])
            for b in blocks:
                if b.get("type") == "tool_use":
                    calls[b["id"]] = b["name"]
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                    key = KEYS[verdict(b)]
                    # A REPL error repeats its inner call's denial, so only the auto check's own stop of it counts.
                    if calls[b["tool_use_id"]] != "REPL" or key == "auto check":
                        count[key] += 1
    code_mode = "on" if "REPL" in calls.values() else "off"
    print(label(folder), ",".join(sorted(version)), code_mode, " ".join(f"{k}={v}" for k, v in count.items()), sep="\t")
