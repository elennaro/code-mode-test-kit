"""PreToolUse hook for the hook check: one line per tool call, written next to the run folder (<cwd>.hooks.txt)."""
import json
import sys

call = json.load(sys.stdin)
args = call.get("tool_input") or {}
detail = args.get("command") or args.get("file_path") or args.get("pattern") or ""
with open(call["cwd"].rstrip("\\/") + ".hooks.txt", "a", encoding="utf-8") as f:
    f.write(f"{call.get('tool_name', '')} {detail}".strip().replace("\n", " ") + "\n")
