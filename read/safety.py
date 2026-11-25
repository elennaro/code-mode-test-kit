"""Print what each safety run tried and what stopped it. Usage: python safety.py <log folder>...

For every tool call: the tool, the start of its command or code, and, when it failed, the start of the error.
Also the model the run used, because a refusal can switch it.
"""
import glob
import json
import sys

from logs import folders, label


def short(text: str, n: int = 160) -> str:
    return " ".join(str(text).split())[:n]


for folder in folders(sys.argv[1:]):
    calls, models = {}, set()
    print(f"== {label(folder)}")
    paths = glob.glob(folder + "/*.jsonl")
    if len(paths) > 1:
        sys.exit(f"{folder} holds {len(paths)} sessions; one run folder must hold one session")
    for path in paths:
        for line in open(path, encoding="utf-8"):
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") not in ("user", "assistant"):  # e.g. api-request-blob rows repeat earlier calls
                continue
            m = o.get("message") or {}
            if m.get("model") and m["model"] != "<synthetic>":
                models.add(m["model"])
            content = m.get("content")
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("id") not in calls:  # a call logged twice: print it once
                    inp = b.get("input", {})
                    what = inp.get("command") or inp.get("code") or inp.get("file_path") or json.dumps(inp)
                    calls[b["id"]] = b["name"]
                    print(f"  call {b['name']}: {short(what)}")
                elif b.get("type") == "tool_result" and b.get("is_error"):
                    c = b.get("content") or ""
                    text = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                    print(f"  ERROR {calls.get(b.get('tool_use_id'), '?')}: {short(text, 220)}")
    print(f"  models: {', '.join(sorted(models))}")
