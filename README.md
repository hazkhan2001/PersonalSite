# Hamza's Library

A personal library site built by a small Python script. You write plain text files; `build.py` turns them into web pages.

## Setup (once)

```
pip install -r requirements.txt
```

## Everyday use

```
python build.py serve
```

This builds the site and starts a preview at http://localhost:8000. Press Ctrl+C to stop. Use `python build.py` on its own to build without previewing.

After every build the script prints how many entries each section has, plus a list of **things to check** (a missing field, a manuscript pointing to a script that doesn't exist, and so on). Problem entries are skipped rather than breaking the build, so read that list.

## Where everything lives

| Path | What it holds |
|---|---|
| `site.yaml` | Site title, intro, navigation, and every section's title and introduction |
| `content/essays/`, `content/analysis/`, `content/reviews/` | One Markdown file per piece of writing |
| `content/pages/` | Standalone pages such as About |
| `content/data/manuscripts.yaml` | The manuscript collection |
| `content/data/scripts.yaml` | The Arabic scripts |
| `content/data/image_collections.yaml` | The groups in the Images section (Ka'ba, mosques, war, ...) |
| `content/data/images.yaml` | Historical images, each with credit, context, and your note |
| `content/data/poetry.yaml` | Poetry, idioms, and proverbs |
| `content/data/books.yaml` | Books reading, read, and to read |
| `content/data/projects.yaml` | Projects |
| `content/data/languages.yaml` | Languages and skills (shown on About) |
| `static/style.css` | Layout and spacing, shared by every theme |
| `static/themes/` | Colours and fonts, one file per theme (pick one in `site.yaml`) |
| `static/site.js` | Filter buttons and the show-image button for sensitive images |
| `static/images/` | Your own images, e.g. manuscript photos |
| `templates/` | The HTML layout for each kind of page |
| `build.py` | The generator |
| `new.py` | Starts a new essay, analysis, or review |

`output/` is the finished site. It's rebuilt from scratch every time, so never edit it by hand.

## Changing the look

The site has three themes, each one small file in `static/themes/`:

- **verdigris**: grey-green paper, green-black ink, Alegreya
- **lapis**: deep blue page with gold, Spectral
- **ledger**: cool white, slate and accounting red, Libre Franklin and Gelasio

Switch with the `theme:` line in `site.yaml`. To make your own, copy one of the files, rename it, change the colours and fonts at the top, and put its name in `theme:`. Layout lives in `static/style.css` and is shared by every theme.

## Adding things

**Writing.** `python new.py essay "Title"` (or `analysis`, `review`) creates the file with today's date. It starts as a draft; delete the `draft: true` line when it's ready.

**Everything else.** Each YAML file in `content/data/` begins with a comment listing its fields. Copy an existing entry, paste it, and change the values. YAML is picky about two things:

- Indentation must line up, using spaces, never tabs.
- Put text in "quotes" if it contains a colon (`:`) or starts with a special character.

**Manuscript photos.** Put them in `static/images/manuscripts/` and see the README there.

**Images.** Add a collection to `image_collections.yaml` once, then add images to `images.yaml` with `collection:` set to its id. Each collection sorts itself by `year`. Mark war or death imagery with `sensitive:` and a short content note, and it stays blurred until a visitor chooses to see it. For photographs still in copyright, set `source: copyrighted`, leave out `src`, and give the `link` instead: the page links to the image rather than copying it. The comments at the top of `images.yaml` explain each field.

**Poetry in a new language.** Add the language to `LANGUAGE_CODES` in `build.py`. If it's written right to left, add its code to `RTL_CODES` as well.

## Publishing on GitHub Pages

1. Create a GitHub repository. Naming it `hazkhan2001.github.io` publishes the site at https://hazkhan2001.github.io. Any other name, say `library`, publishes at https://hazkhan2001.github.io/library; in that case set `base_url: "/library"` in `site.yaml`.
2. Upload this folder to the repository.
3. On GitHub: Settings > Pages > Source: **GitHub Actions**.

From then on, every change pushed to the repository rebuilds the site automatically (see `.github/workflows/deploy.yml`). That includes edits made in GitHub's web editor, which works from a phone.

The site lives at https://hazkhan2001.github.io/PersonalSite. `python build.py serve` ignores `base_url` while previewing, so local previews work without changing anything.
