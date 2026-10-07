"""
build.py: turns the content/ folder into a finished website in output/.

    python build.py          build the site into output/
    python build.py serve    build it, then preview at http://localhost:8000

The file is organised top to bottom as:
    1. imports and settings
    2. loading content (Markdown files and YAML data files)
    3. template filters (small helpers the HTML templates can call)
    4. one "builder" function per section of the site
    5. build(), which runs every builder in order
"""

# ===========================================================================
# 1. Imports and settings
# ===========================================================================
import shutil
import sys
from collections import defaultdict
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
DATA = CONTENT / "data"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
OUTPUT = ROOT / "output"

# Writing sections: folder name -> the label for one piece in that folder.
WRITING_SECTIONS = {
    "essays": "Essay",
    "analysis": "Analysis",
    "reviews": "Review",
}

# Language name -> standard language code. The code tells browsers (and
# screen readers) what language a line is in, and picks the right font.
# Add a line here when you add poetry in a new language.
LANGUAGE_CODES = {
    "Arabic": "ar",
    "Persian": "fa",
    "Dari": "fa",
    "Urdu": "ur",
    "Pashto": "ps",
    "Ottoman Turkish": "ota",
    "Turkish": "tr",
    "Punjabi": "pa",
    "Hindi": "hi",
    "English": "en",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Latin": "la",
    "Greek": "el",
    "Chinese": "zh",
    "Malay": "ms",
}

# Codes of languages written right to left. A set is like a list, but
# checking "is x in this set?" is instant and duplicates are impossible.
RTL_CODES = {"ar", "fa", "ur", "ps", "ota"}

SOURCE_LABELS = {
    "public-domain": "Public domain",
    "own-photo": "My photograph",
    "licensed": "Used under an open licence",
    "copyrighted": "In copyright, linked rather than reproduced",
}

BOOK_STATUSES = {"reading", "finished", "to-read"}

# Problems found while building are collected here and printed at the end,
# so one bad entry never stops the whole site from building.
WARNINGS = []


def warn(message):
    WARNINGS.append(message)


# ===========================================================================
# 2. Loading content
# ===========================================================================
def to_html(text):
    """Convert Markdown text to HTML.

    Markup() marks the result as safe HTML, so templates show it as
    formatting rather than as literal <p> tags. It's the Python-side
    version of the "| safe" filter you met in step 1.
    """
    return Markup(markdown.markdown(text or "", extensions=["extra"]))


def read_markdown_file(path):
    """Read one .md file: front matter becomes a dictionary, body becomes HTML."""
    text = path.read_text(encoding="utf-8")

    if text.startswith("---"):
        _, front_matter, body = text.split("---", 2)
        info = yaml.safe_load(front_matter) or {}
    else:
        info, body = {}, text

    info["html"] = to_html(body)
    info["slug"] = path.stem
    # Reading time: roughly 230 words a minute, and never less than 1.
    info["minutes"] = max(1, round(len(body.split()) / 230))
    return info


def load_markdown_folder(folder):
    """Every published .md file in a folder, newest first."""
    entries = []
    for path in sorted(folder.glob("*.md")):
        entry = read_markdown_file(path)
        if entry.get("draft"):
            continue
        if not entry.get("title"):
            warn(f"{path.relative_to(ROOT)} has no title")
            entry["title"] = entry["slug"].replace("-", " ").capitalize()
        entries.append(entry)

    entries.sort(key=lambda e: str(e.get("date", "")), reverse=True)
    return entries


def load_data(name, required=()):
    """Load content/data/<name>.yaml, a list of entries.

    Entries missing a required field are skipped with a warning, so a
    half-finished entry can't break the pages built from the rest.
    """
    path = DATA / f"{name}.yaml"
    if not path.exists():
        warn(f"{path.relative_to(ROOT)} not found, so that section is empty")
        return []

    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    valid = []
    # enumerate() hands back a counter alongside each item.
    for number, entry in enumerate(entries, start=1):
        missing = [field for field in required if not entry.get(field)]
        if missing:
            label = entry.get("title") or entry.get("name") or f"entry #{number}"
            warn(f"{path.name}: skipped {label}, missing {', '.join(missing)}")
            continue
        valid.append(entry)
    return valid


# ===========================================================================
# 3. Template filters: used in templates as {{ value | filter_name }}
# ===========================================================================
def nice_date(d):
    """2026-10-07 -> 'October 7, 2026'."""
    if not d:
        return ""
    return f"{d:%B} {d.day}, {d.year}"


def rfc822(d):
    """The date format RSS feeds require: 'Wed, 07 Oct 2026 00:00:00 +0000'."""
    if not d:
        return ""
    return d.strftime("%a, %d %b %Y 00:00:00 +0000")


def ordinal(n):
    """7 -> '7th', 21 -> '21st', 12 -> '12th'."""
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"            # 11th, 12th, 13th are the exceptions
    else:
        # dict.get(key, default): look the key up, fall back to "th"
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def year_label(year):
    """1880 -> '1880', -500 -> '500 BCE'. Negative numbers are years BCE."""
    if not year and year != 0:      # nothing there (None, "", or missing)
        return ""
    year = int(year)
    return f"{-year} BCE" if year < 0 else str(year)


def stars(rating):
    """4 -> '★★★★☆'. Multiplying a string repeats it."""
    rating = max(0, min(5, int(rating or 0)))
    return "★" * rating + "☆" * (5 - rating)


def make_environment(site):
    """Set up Jinja with our templates, filters and site-wide settings."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=True,
        trim_blocks=True,       # tidier HTML: no blank lines left by {% %} tags
        lstrip_blocks=True,
    )
    base = site.get("base_url", "")

    # These two are defined inside make_environment so they can "remember"
    # base_url. A function that uses a variable from its surroundings like
    # this is called a closure.
    def link(path):
        """'/essays/' -> '/essays/', or '/library/essays/' if base_url is set."""
        return base + path

    def image_src(src):
        """Web addresses pass through; local files point into static/images/."""
        if not src:
            return ""
        if src.startswith(("http://", "https://")):
            return src
        return f"{base}/static/images/{src}"

    env.globals["site"] = site
    env.filters.update(
        link=link,
        image_src=image_src,
        nice_date=nice_date,
        rfc822=rfc822,
        ordinal=ordinal,
        year=year_label,
        stars=stars,
        md=to_html,
    )
    return env


def render(env, template_name, url, **context):
    """Fill a template and save it at the place matching its URL.

    "/essays/x/" is saved as output/essays/x/index.html, which is why
    addresses can end in a clean slash. "/feed.xml" is saved as-is.
    """
    if url.endswith("/"):
        out_path = OUTPUT / url.strip("/") / "index.html"
    else:
        out_path = OUTPUT / url.strip("/")
    html = env.get_template(template_name).render(**context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


# ===========================================================================
# 4. Builders: one per section of the site
# ===========================================================================
def build_writing(env):
    """Essays, analysis and reviews: a page for each piece, a list per
    section, and one combined Writing page."""
    by_section = {}
    all_writing = []

    # .items() gives (key, value) pairs, unpacked into two names.
    for key, kind in WRITING_SECTIONS.items():
        entries = load_markdown_folder(CONTENT / key)
        for entry in entries:
            entry["section"] = key
            entry["kind"] = kind
            entry["url"] = f"/{key}/{entry['slug']}/"
            render(env, "prose.html", entry["url"], entry=entry, section="writing")

        render(env, "prose_list.html", f"/{key}/",
               key=key, entries=entries, section="writing")
        by_section[key] = entries
        all_writing.extend(entries)      # extend adds every item of a list

    all_writing.sort(key=lambda e: str(e.get("date", "")), reverse=True)

    # Filter buttons only for sections that have something in them.
    kind_options = [(key, env.globals["site"]["sections"][key]["title"])
                    for key in WRITING_SECTIONS if by_section[key]]
    render(env, "writing.html", "/writing/",
           entries=all_writing, kind_options=kind_options, section="writing")
    return by_section, all_writing


def build_books(env, reviews):
    books = load_data("books", required=["title", "author", "status"])

    # A set comprehension: every review slug, for quick lookups.
    review_slugs = {review["slug"] for review in reviews}

    for book in books:
        if book["status"] not in BOOK_STATUSES:
            warn(f"books.yaml: {book['title']} has status '{book['status']}', "
                 f"expected one of {', '.join(sorted(BOOK_STATUSES))}")
        slug = book.get("review")
        if slug:
            if slug in review_slugs:
                book["review_url"] = f"/reviews/{slug}/"
            else:
                warn(f"books.yaml: {book['title']} links to a review '{slug}' that doesn't exist")

    # List comprehensions: "keep each book whose status is ...".
    reading = [b for b in books if b["status"] == "reading"]
    to_read = [b for b in books if b["status"] == "to-read"]

    # defaultdict(list) creates an empty list the first time a year appears,
    # so we can append without checking whether the key exists yet.
    finished = defaultdict(list)
    for book in books:
        if book["status"] == "finished":
            finished[book.get("year", "Undated")].append(book)
    years = sorted(finished, key=str, reverse=True)

    render(env, "books.html", "/books/", reading=reading, finished=finished,
           years=years, to_read=to_read, total=len(books), section="books")
    return books


def build_manuscripts_and_scripts(env):
    scripts = load_data("scripts", required=["id", "name", "summary"])
    manuscripts = load_data("manuscripts", required=["id", "title", "script"])

    scripts.sort(key=lambda s: s.get("from_century", 99))

    # A dict comprehension: script id -> script. This is how a manuscript
    # saying `script: kufic` finds the full Kufic record.
    scripts_by_id = {script["id"]: script for script in scripts}

    for script in scripts:
        script["url"] = f"/scripts/{script['id']}/"
        script["html"] = to_html(script.get("description"))
        script["manuscripts"] = []        # filled in by the loop below

    for ms in manuscripts:
        ms["url"] = f"/manuscripts/{ms['id']}/"
        ms["html"] = to_html(ms.get("description"))
        ms["images"] = ms.get("images") or []
        ms["cover"] = ms["images"][0] if ms["images"] else None
        ms["source_label"] = SOURCE_LABELS.get(ms.get("source"), "")

        script = scripts_by_id.get(ms["script"])
        if script is None:
            warn(f"manuscripts.yaml: {ms['title']} uses script '{ms['script']}', "
                 "which isn't in scripts.yaml")
        else:
            script["manuscripts"].append(ms)   # the reverse link: script -> manuscripts
        ms["script_info"] = script

    # Options for the filter buttons, built only from values actually in use.
    filters = {
        "script": [(s["id"], s["name"]) for s in scripts if s["manuscripts"]],
        "century": [(str(c), f"{ordinal(c)} c.")
                    for c in sorted({ms["century"] for ms in manuscripts if ms.get("century")})],
        "source": [(key, SOURCE_LABELS[key])
                   for key in SOURCE_LABELS
                   if any(ms.get("source") == key for ms in manuscripts)],
    }

    for ms in manuscripts:
        render(env, "manuscript.html", ms["url"], ms=ms, section="manuscripts")
    render(env, "manuscripts.html", "/manuscripts/",
           manuscripts=manuscripts, filters=filters, section="manuscripts")

    for script in scripts:
        render(env, "script.html", script["url"], script=script, section="scripts")
    render(env, "scripts.html", "/scripts/", scripts=scripts, section="scripts")

    return manuscripts, scripts


def build_images(env):
    """Historical images, grouped into collections such as 'The Ka'ba
    through time'. Each collection is shown oldest first, and each image
    page links to the one before and after it in its collection."""
    collections = load_data("image_collections", required=["id", "title"])
    images = load_data("images", required=["id", "title", "collection"])

    collections_by_id = {c["id"]: c for c in collections}
    for collection in collections:
        collection["url"] = f"/images/{collection['id']}/"
        collection["intro_html"] = to_html(collection.get("intro"))
        collection["images"] = []

    placed = []      # images whose collection exists
    for image in images:
        collection = collections_by_id.get(image["collection"])
        if collection is None:
            warn(f"images.yaml: {image['title']} is in collection "
                 f"'{image['collection']}', which isn't in image_collections.yaml")
            continue

        image["url"] = f"{collection['url']}{image['id']}/"
        image["collection_info"] = collection
        image["note_html"] = to_html(image.get("note"))
        image["context_html"] = to_html(image.get("context"))
        image["source_label"] = SOURCE_LABELS.get(image.get("source"), "")
        image["medium_key"] = (image.get("medium") or "").lower().replace(" ", "-")

        # isinstance() checks a value's type. Sorting needs whole numbers,
        # so text like "c. 1880" belongs in `date`, not `year`.
        if "year" in image and not isinstance(image["year"], int):
            warn(f"images.yaml: {image['title']} has year '{image['year']}'. "
                 "Use a whole number (e.g. 1880) and put wording in `date`.")
            image.pop("year")

        if image.get("source") == "copyrighted" and image.get("src"):
            warn(f"images.yaml: {image['title']} is marked copyrighted but has an "
                 "image file. Consider removing src and keeping only the link.")
        if not image.get("src") and not image.get("link"):
            warn(f"images.yaml: {image['title']} has no image (src) or link yet")

        collection["images"].append(image)
        placed.append(image)

    for collection in collections:
        items = collection["images"]
        # Oldest first. Images without a year go to the end (9999).
        items.sort(key=lambda image: image.get("year", 9999))

        # Link each image to its neighbours. enumerate() gives the position,
        # so items[i - 1] is the one before and items[i + 1] the one after.
        for i, image in enumerate(items):
            image["prev"] = items[i - 1] if i > 0 else None
            image["next"] = items[i + 1] if i < len(items) - 1 else None

        # The span of years covered, e.g. "1855 to 1885".
        years = [image["year"] for image in items if image.get("year") is not None]
        if years:
            first, last = year_label(min(years)), year_label(max(years))
            collection["span"] = first if first == last else f"{first} to {last}"
        else:
            collection["span"] = ""

        # The cover: the chosen image, or else the first one that has a file
        # and isn't marked sensitive.
        chosen = collection.get("cover")
        collection["cover_image"] = next(
            (image for image in items
             if (image["id"] == chosen) or (not chosen and image.get("src") and not image.get("sensitive"))),
            None,
        )

        medium_options = sorted({(image["medium_key"], image["medium"])
                                 for image in items if image.get("medium")})
        render(env, "image_collection.html", collection["url"],
               collection=collection, medium_options=medium_options, section="images")
        for image in items:
            render(env, "image.html", image["url"], image=image, section="images")

    render(env, "images.html", "/images/", collections=collections, section="images")
    return placed, collections


def build_poetry(env):
    poems = load_data("poetry", required=["original", "language", "translation"])

    for poem in poems:
        code = LANGUAGE_CODES.get(poem["language"])
        if code is None:
            warn(f"poetry.yaml: unknown language '{poem['language']}'. "
                 "Add it to LANGUAGE_CODES in build.py")
            code = ""
        poem["lang"] = code
        poem["dir"] = "rtl" if code in RTL_CODES else "ltr"
        poem["filter_key"] = poem["language"].lower().replace(" ", "-")
        poem["kind"] = poem.get("kind", "verse")
        # .strip() removes the trailing newline YAML leaves on multi-line text
        for field in ("original", "transliteration", "translation"):
            if poem.get(field):
                poem[field] = poem[field].strip()
        poem["note_html"] = to_html(poem.get("note"))

    language_options = sorted({(p["filter_key"], p["language"]) for p in poems},
                              key=lambda option: option[1])
    kind_options = [(k, k.capitalize()) for k in sorted({p["kind"] for p in poems})]

    render(env, "poetry.html", "/poetry/", poems=poems,
           language_options=language_options, kind_options=kind_options,
           section="poetry")
    return poems


def build_projects(env):
    projects = load_data("projects", required=["name", "summary"])
    for project in projects:
        project["html"] = to_html(project.get("description"))
    render(env, "projects.html", "/projects/", projects=projects, section="projects")
    return projects


def build_pages(env):
    """Standalone pages from content/pages/. About also lists languages."""
    languages = load_data("languages", required=["name", "level"])
    for item in languages:
        item.setdefault("group", "Languages")   # fill in only if it's missing
    pages =load_markdown_folder(CONTENT / "pages")
    for page in pages:
        render(env, "page.html", f"/{page['slug']}/",
               page=page, languages=languages, section=page["slug"])
    return pages


def build_home(env, writing, manuscripts, poems, counts):
    # next() returns the first item a generator produces, or the default
    # (here None) if it produces nothing: "the first featured poem, if any".
    featured = next((p for p in poems if p.get("featured")), None)
    if featured is None and poems:
        featured = poems[0]

    render(env, "home.html", "/", recent=writing[:5],
           manuscripts=manuscripts[:3], featured=featured, counts=counts,
           section="home")


# ===========================================================================
# 5. The full build
# ===========================================================================
def build(preview=False):
    site = yaml.safe_load((ROOT / "site.yaml").read_text(encoding="utf-8"))

    # On GitHub the site lives under /HK.Site, but a local preview serves it
    # from the top level, so the preview ignores base_url.
    if preview:
        site["base_url"] = ""

    # Start fresh each time so deleted content doesn't linger.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(STATIC, OUTPUT / "static")

    env = make_environment(site)

    by_section, writing = build_writing(env)
    books = build_books(env, by_section["reviews"])
    manuscripts, scripts = build_manuscripts_and_scripts(env)
    images, image_collections = build_images(env)
    poems = build_poetry(env)
    projects = build_projects(env)
    build_pages(env)

    counts = {
        "writing": len(writing),
        "manuscripts": len(manuscripts),
        "scripts": len(scripts),
        "images": len(images),
        "poetry": len(poems),
        "books": len(books),
        "projects": len(projects),
    }
    build_home(env, writing, manuscripts, poems, counts)
    render(env, "feed.xml", "/feed.xml", entries=writing[:20])
    render(env, "404.html", "/404.html")

    print("Built the site into output/")
    for name, count in counts.items():
        print(f"  {name:<12} {count}")      # :<12 pads the name to 12 characters

    if WARNINGS:
        print(f"\n{len(WARNINGS)} thing(s) to check:")
        for message in WARNINGS:
            print(f"  - {message}")


def serve(port=8000):
    """Preview the built site locally. partial() pre-fills an argument
    (here, which folder to serve) so the server can create handlers itself."""
    handler = partial(SimpleHTTPRequestHandler, directory=OUTPUT)
    print(f"\nPreviewing at http://localhost:{port}  (press Ctrl+C to stop)")
    with ThreadingHTTPServer(("", port), handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    previewing = "serve" in sys.argv[1:]     # sys.argv: the words typed after "python"
    build(preview=previewing)
    if previewing:
        serve()
