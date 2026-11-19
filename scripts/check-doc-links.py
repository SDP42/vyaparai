"""Report Markdown links and images to files or headings that do not exist.

Usage: python3 scripts/check-doc-links.py   (from the repository root; exit code 1 when a link is broken)

Checks every *.md file outside node_modules, .venv and .next. External links (http, mailto) are skipped.
A link to `file.md#heading` is checked against the headings of that file, slugged the way GitHub does.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"node_modules", ".venv", ".next", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMG = re.compile(r"<img[^>]+src=\"([^\"]+)\"")
FENCE = re.compile(r"^(```|~~~)")


def slug(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code and line.startswith("#"):
            base = slug(line.lstrip("#"))
            n = seen.get(base, 0)
            seen[base] = n + 1
            found.add(base if n == 0 else f"{base}-{n}")
    return found


def files() -> list[Path]:
    return [
        p for p in ROOT.rglob("*.md") if not any(part in SKIP for part in p.relative_to(ROOT).parts)
    ]


def main() -> int:
    broken: list[str] = []
    for md in sorted(files()):
        in_code = False
        for no, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if FENCE.match(line):
                in_code = not in_code
                continue
            if in_code:
                continue
            for target in LINK.findall(line) + IMG.findall(line):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, _, frag = target.partition("#")
                dest = md if not path_part else (md.parent / path_part).resolve()
                where = f"{md.relative_to(ROOT)}:{no}"
                if not dest.exists():
                    broken.append(f"{where}  missing file  {target}")
                elif frag and dest.suffix == ".md" and frag.lower() not in anchors(dest):
                    broken.append(f"{where}  missing heading  {target}")
    for item in broken:
        print(item)
    print(f"{len(broken)} broken link(s)")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
