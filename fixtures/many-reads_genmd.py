"""Make a project of 300 linked Markdown files with 15 broken local links, for the Many small reads test.

Usage: python many-reads_genmd.py <new folder>   writes the project
       python many-reads_genmd.py --broken       prints the broken links (file: link), to check an answer
The same files every time. The answer list is never written into the folder, so the model cannot read it.
"""
import random
import sys
from pathlib import Path

AREAS = ["guides", "reference", "notes", "howto", "design", "ops"]
WORDS = ("cache queue worker build release test config index search report "
         "parser upload backup token session render export import schedule").split()
FILES, BROKEN_COUNT = 300, 15


def plan() -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Each file's links, relative to the file, and the broken ones as (file, link)."""
    rng = random.Random(7)
    paths = ["README.md"] + [f"{AREAS[i % len(AREAS)]}/{rng.choice(WORDS)}-{i:03}.md" for i in range(1, FILES)]
    links: dict[str, list[str]] = {}
    for p in paths:
        here = Path(p).parent
        targets = rng.sample([q for q in paths if q != p], 3)
        links[p] = [Path(*[".."] * len(here.parts), q).as_posix() if here.parts else q for q in targets]
    broken = []
    for p in rng.sample(paths[1:], BROKEN_COUNT):
        link = f"../{rng.choice(AREAS)}/missing-{rng.choice(WORDS)}.md"
        links[p].append(link)
        broken.append((p, link))
    return links, sorted(broken)


def write(root: Path) -> None:
    links, _ = plan()
    for p, out in links.items():
        f = root / p
        f.parent.mkdir(parents=True, exist_ok=True)
        title = Path(p).stem.replace("-", " ").title()
        body = "\n".join(f"- [{Path(link).stem}]({link})" for link in out)
        f.write_text(f"# {title}\n\nNotes for this part of the project.\n\nSee also:\n\n{body}\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["--broken"]:
        print("\n".join(f"{p}: {link}" for p, link in plan()[1]))
    elif len(sys.argv) == 2 and not Path(sys.argv[1]).exists():
        write(Path(sys.argv[1]))
    else:
        sys.exit("usage: many-reads_genmd.py <new folder> | --broken")
