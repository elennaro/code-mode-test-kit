"""Hook check fixture: a small git repo with three commits and one uncommitted change.

Usage: python hook-check_repo.py FOLDER
The prompt asks for git status, the last three commits and the first five lines of README.md, so the folder
needs all three to give a non-empty answer.
"""
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
root.mkdir(parents=True)
env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "",
       "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": ""}


def git(*args):
    subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True)


git("init", "-q", "-b", "main")
(root / "README.md").write_text("# Notes tool\n\nA small tool that sorts notes by date.\n\n"
                                "Run `python notes.py` to print them.\n\nNo settings are needed.\n", encoding="utf-8")
git("add", "README.md")
git("commit", "-q", "-m", "Add README")
(root / "notes.py").write_text("print('no notes yet')\n", encoding="utf-8")
git("add", "notes.py")
git("commit", "-q", "-m", "Add notes script")
(root / "notes.txt").write_text("2026-01-02 buy milk\n", encoding="utf-8")
git("add", "notes.txt")
git("commit", "-q", "-m", "Add sample notes")
(root / "notes.txt").write_text("2026-01-02 buy milk\n2026-01-03 call back\n", encoding="utf-8")  # uncommitted
assert subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True).stdout.strip() == "M notes.txt"
