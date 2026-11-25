"""Helpers for the readers: which log folders to read, and the short name of a run."""
import glob
import os
from pathlib import Path


def folders(args: list[str]) -> list[str]:
    """Expand ~ and * in the arguments ourselves: Windows PowerShell 5.1 passes them to Python as they are."""
    out = []
    for arg in args:
        arg = os.path.expanduser(arg)
        out += sorted(glob.glob(arg)) if glob.has_magic(arg) else [arg]
    return out


def prompt_text(row: dict) -> str:
    """The text of a prompt the user typed, or "" for any other row.

    Claude Code also logs its own notes as user rows marked isMeta, such as the output of /context;
    tool results and local commands are not prompts either.
    """
    content = (row.get("message") or {}).get("content")
    if row.get("type") != "user" or row.get("isMeta"):
        return ""
    text = content if isinstance(content, str) else " ".join(
        p.get("text", "") for p in content or [] if isinstance(p, dict) and p.get("type") == "text")
    return "" if text.lstrip().startswith(("<command-", "<local-command-")) else text


def label(folder: str) -> str:
    """Claude Code names a log folder after the run's working folder, with every other character as '-'.

    A run folder is named by a neutral id of letters and digits (r07), so the id is the last part.
    The "Delete outside" test runs in <run folder>/project.
    """
    return Path(folder.rstrip("/\\")).name.removesuffix("-project").rsplit("-", 1)[-1]
