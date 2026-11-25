"""Per-turn cost of one long session: gap before the turn, requests, cache writes, cache read, list-price cost.

Usage: python perturn.py FOLDER... (each a ~/.claude/projects/<cwd> folder). Same prices and rules as runs.py.
A turn starts at a prompt typed after the previous turn ended, so the turns of a session continued with
--continue are counted in order.
"""
import glob
import json
import sys
from datetime import datetime

from logs import folders, label, prompt_text

BASE, OUT, READ, W5, W1 = 4.0, 20.0, 0.05, 1.25, 2.0  # the same prices as runs.py

for folder in folders(sys.argv[1:]):
    print("==", label(folder))
    print("turn\tgap_s\treq\tw5m\tw1h\tread\tinput\tout\tusd")
    turns, seen, cur, last_end = [], set(), None, None
    paths = glob.glob(folder + "/*.jsonl")
    if len(paths) > 1:  # --continue appends to one file; a second file is another session
        sys.exit(f"{folder} holds {len(paths)} sessions; one run folder must hold one session")
    # shortcut: a turn stopped before its answer merges with the next one; none of the original turns was stopped
    for path in paths:
        for line in open(path, encoding="utf-8"):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("isSidechain"):
                continue
            msg = row.get("message") or {}
            ts = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) if "timestamp" in row else None
            if prompt_text(row) and (cur is None or cur["ended"]):
                cur = {"gap": round((ts - last_end).total_seconds()) if last_end and ts else 0,
                       "req": 0, "w5": 0, "w1": 0, "read": 0, "fresh": 0, "out": 0, "ended": False}
                turns.append(cur)
            if cur is None or row.get("type") != "assistant":
                continue
            if msg.get("stop_reason") == "end_turn":
                cur["ended"], last_end = True, ts
            u = msg.get("usage")
            if not u or msg.get("id") in seen or msg.get("model") == "<synthetic>":
                continue
            seen.add(msg.get("id"))
            one_hour = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
            cur["req"] += 1
            cur["w1"] += one_hour
            cur["w5"] += u.get("cache_creation_input_tokens", 0) - one_hour
            cur["read"] += u.get("cache_read_input_tokens", 0)
            cur["fresh"] += u.get("input_tokens", 0)
            cur["out"] += u.get("output_tokens", 0)
    tot = 0.0
    for i, t in enumerate(turns, 1):
        usd = (t["fresh"] + t["w5"] * W5 + t["w1"] * W1 + t["read"] * READ) * BASE / 1e6 + t["out"] * OUT / 1e6
        tot += usd
        total_in = t["fresh"] + t["w5"] + t["w1"] + t["read"]
        print(f"{i}\t{t['gap']}\t{t['req']}\t{t['w5']}\t{t['w1']}\t{t['read']}\t{total_in}\t{t['out']}\t{usd:.4f}")
    print(f"total\t\t\t\t\t\t\t\t{tot:.4f}")
