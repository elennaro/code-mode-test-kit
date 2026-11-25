"""Write four made-up service logs with one incident: storage disk fills at 02:14:07 and the failure spreads."""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
rnd = random.Random(7)
start = datetime(2026, 11, 20, 1, 0, 0)
incident = datetime(2026, 11, 20, 2, 14, 7)
LINES = 2500

normal = {
    "gateway": ["GET /thumb/{id} 200 {ms}ms", "GET /health 200 2ms", "POST /upload 201 {ms}ms"],
    "resizer": ["resized image {id} to 320x240 in {ms}ms", "resized image {id} to 1280x960 in {ms}ms", "cache hit for {id}"],
    "storage": ["wrote object {id} ({kb} KB)", "read object {id} ({kb} KB)", "disk usage {pct}%"],
    "queue": ["enqueued job {id}", "dequeued job {id}", "queue depth {depth}"],
}
bad = {
    "gateway": ("ERROR", "GET /thumb/{id} 504 upstream timeout after 30000ms"),
    "resizer": ("ERROR", "failed to save image {id}: storage write failed"),
    "storage": ("ERROR", "write object {id} failed: No space left on device"),
    "queue": ("WARN", "queue depth {depth} above limit 500, consumers falling behind"),
}
lag = {"storage": 0, "resizer": 20, "queue": 75, "gateway": 140}  # seconds after the incident

for svc, msgs in normal.items():
    t = start
    rows = []
    for i in range(LINES):
        t += timedelta(seconds=rnd.uniform(1.0, 3.6))
        failing = t >= incident + timedelta(seconds=lag[svc]) and rnd.random() < 0.6
        if failing:
            level, msg = bad[svc]
        else:
            level, msg = ("INFO", rnd.choice(msgs))
        pct = min(100, 71 + int((t - start).total_seconds() / 153)) if svc == "storage" else 0
        depth = 40 + rnd.randint(0, 30) + (max(0, int((t - incident).total_seconds())) * 3 if t > incident else 0)
        msg = msg.format(id=rnd.randint(10000, 99999), ms=rnd.randint(8, 240), kb=rnd.randint(40, 900), pct=pct, depth=depth)
        rows.append(f"{t:%Y-%m-%d %H:%M:%S} {level:<5} [{svc}] {msg}")
    (out / f"{svc}.log").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(svc, len(rows), rows[-1][:19])
