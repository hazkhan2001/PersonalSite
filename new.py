"""
new.py: start a new piece of writing with the front matter already filled in.

    python new.py essay "On the Ottoman mint"
    python new.py analysis "Who finances Pakistan"
    python new.py review "The Muqaddimah"

The new file is marked as a draft, so it stays hidden until you delete
the `draft: true` line.
"""
import re
import sys
from datetime import date
from pathlib import Path

FOLDERS = {"essay": "essays", "analysis": "analysis", "review": "reviews"}


def slugify(title):
    """'On the Ottoman Mint!' -> 'on-the-ottoman-mint'."""
    slug = title.lower()
    # A regular expression: [^a-z0-9]+ means "one or more characters that are
    # NOT a lowercase letter or digit". Each such run becomes a single hyphen.
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in FOLDERS:
        print(__doc__)          # __doc__ is the description at the top of this file
        sys.exit(1)

    kind = sys.argv[1]
    title = " ".join(sys.argv[2:])
    slug = slugify(title) or f"untitled-{date.today()}"

    folder = Path(__file__).parent / "content" / FOLDERS[kind]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug}.md"
    if path.exists():
        print(f"{path.name} already exists, so nothing was created.")
        sys.exit(1)

    safe_title = title.replace('"', '\\"')     # escape quotes for YAML
    lines = [
        "---",
        f'title: "{safe_title}"',
        f"date: {date.today()}",
        'summary: ""',
        "tags: []",
    ]
    if kind == "review":
        lines += ['book: ""', 'author: ""', "rating: 0"]
    lines += ["draft: true", "---", "", "Start writing here.", ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created content/{FOLDERS[kind]}/{path.name} (hidden as a draft for now)")


if __name__ == "__main__":
    main()
