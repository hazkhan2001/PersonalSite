---
title: How this site works
date: 2026-10-07
summary: A sample essay that doubles as a cheat sheet. Delete it once you've written your first real one.
tags: [meta, notes]
---

Every essay on this site is a plain text file in the `content/essays/` folder. The top of the file, between the two `---` lines, is the **front matter**: a few fields that describe the essay. Everything below it is the essay itself, written in Markdown.

## Writing in Markdown

Markdown is ordinary text with a few symbols for formatting:

- A line starting with `##` becomes a heading.
- Wrapping words in `**double asterisks**` makes them **bold**, and `*single asterisks*` make them *italic*.
- A line starting with `>` becomes a block quote.
- `[link text](https://example.com)` makes a link.

> A block quote looks like this, which is handy for quoting a source or a line of verse.

## Adding a new essay

1. Run `python new.py essay "On the Ottoman mint"`. It creates `content/essays/on-the-ottoman-mint.md` with today's date filled in. The file name becomes the web address: `/essays/on-the-ottoman-mint/`.
2. Fill in the summary and tags at the top.
3. Write the essay, then delete the `draft: true` line.
4. Run `python build.py serve` and open http://localhost:8000 to check it.

The same works for `analysis` and `review`.

To keep an essay private while you work on it, add `draft: true` to the front matter. The build will skip it until you remove that line.
