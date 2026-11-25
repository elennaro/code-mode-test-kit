"""Stop hook for long-session.ps1: append the time a turn ended (UTC) to the file named by $LS_MARK."""
import os
from datetime import datetime, timezone

with open(os.environ["LS_MARK"], "a", encoding="utf-8") as f:
    f.write(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "\n")
