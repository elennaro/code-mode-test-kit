"""One row per session in the given Claude Code log folders, named by its [run tag] or its run folder id: time, requests, tokens by kind, tools and list-price cost.

Usage: python runs.py FOLDER... (each a ~/.claude/projects/<cwd> folder). Opus 5.5 list price, per million tokens.
"""
import glob
import json
import sys
from datetime import datetime

from logs import folders, label, prompt_text

BASE, OUT = 4.0, 20.0
READ, WRITE_5M, WRITE_1H = 0.05, 1.25, 2.0

print("run\tdone\tsec\treq\tfirst\tfresh\tw5m\tw1h\tread\tinput\toutput\tresult_chars\tusd\ttools")
for folder in folders(sys.argv[1:]):
    for path in sorted(glob.glob(folder + "/*.jsonl")):
        tag, stamps, seen, called, tools, done, first = None, [], set(), set(), [], False, None
        fresh = w5 = w1 = read = out = chars = 0
        for line in open(path, encoding="utf-8"):
            try:
                row = json.loads(line)
            except ValueError:  # a line still being written
                continue
            msg = row.get("message") or {}
            content = msg.get("content")
            if tag is None and (text := prompt_text(row)):  # the session starts at the first typed prompt
                tag = text[5 : text.index("]")] if text.startswith("[run ") else label(folder)  # the original runs had a [run tag] prompt; new ones are named after their folder
            if tag is None or row.get("isSidechain"):
                continue
            if "timestamp" in row and not row.get("isMeta"):
                stamps.append(datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")))
            if row.get("type") == "user" and isinstance(content, list):
                chars += sum(len(json.dumps(p.get("content", ""))) for p in content if isinstance(p, dict) and p.get("type") == "tool_result")
            if row.get("type") != "assistant":
                continue
            done = done or msg.get("stop_reason") == "end_turn"
            for p in content or []:  # a call logged twice keeps one id: count it once
                if isinstance(p, dict) and p.get("type") == "tool_use" and p.get("id") not in called:
                    called.add(p.get("id"))
                    tools.append(p.get("name", "").split("__")[-1])
            u = msg.get("usage")
            # a tool call made from inside Code Mode is logged as a <synthetic> message: not a model request
            if not u or msg.get("id") in seen or msg.get("model") == "<synthetic>":
                continue
            seen.add(msg.get("id"))
            cc = u.get("cache_creation") or {}
            write = u.get("cache_creation_input_tokens", 0)
            one_hour = cc.get("ephemeral_1h_input_tokens", 0)
            total = u.get("input_tokens", 0) + write + u.get("cache_read_input_tokens", 0)
            first = first or total
            fresh += u.get("input_tokens", 0)
            w1 += one_hour
            w5 += write - one_hour
            read += u.get("cache_read_input_tokens", 0)
            out += u.get("output_tokens", 0)
        if tag is None:
            continue
        usd = (fresh + w5 * WRITE_5M + w1 * WRITE_1H + read * READ) * BASE / 1e6 + out * OUT / 1e6
        sec = round((stamps[-1] - stamps[0]).total_seconds()) if stamps else 0
        calls = ",".join(t for t in tools if t != "Poll")
        print(f"{tag}\t{done}\t{sec}\t{len(seen)}\t{first}\t{fresh}\t{w5}\t{w1}\t{read}\t{fresh + w5 + w1 + read}\t{out}\t{chars}\t{usd:.4f}\t{calls}")
