"""Write the small folder of the simple-steps test (test 7) into the folder given."""
import sys
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
(out / "README.md").write_text("# Sample tools folder\n\nA small folder for a tool test.\nIt has a CSV, a notes file and this README.\n")
(out / "data.csv").write_text("id,name\n" + "".join(f"{i},item{i}\n" for i in range(1, 43)))
(out / "notes.txt").write_text("first note\nTODO: rename the CSV\nsecond note\nTODO: add a header check\n")
(out / "extra.txt").write_text("nothing here\n")
