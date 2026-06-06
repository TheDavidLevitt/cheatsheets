# Cheat Sheets

Single-page HTML quick-references for dev tooling (Git, GitHub, Vim, VS Code, …),
served via GitHub Pages with an auto-generated index.

**Live site:** `https://<username>.github.io/cheatsheets/` (after Pages is enabled)

## How it works

- `sheets/` — one self-contained HTML file per cheat sheet (no external assets).
- `scripts/build_index.py` — scans `sheets/`, extracts each page's title/subtitle,
  and assembles the site into `_site/` (index + copies of the sheets).
- `.github/workflows/pages.yml` — GitHub Actions workflow: on every push to
  `main` it runs the build script and deploys `_site/` to GitHub Pages.

So adding a sheet = drop an HTML file in `sheets/`, commit, push. The index
updates itself.

## Adding a sheet

1. Create a self-contained `*.html` in `sheets/` (inline CSS, no external files).
2. Give it a real `<title>` and a `<p class="sub">one-line description</p>` —
   the index uses both.
3. Commit and push (or open a PR).

## Contributing

PRs welcome — fixes, new sheets, better mnemonics. Keep sheets self-contained
(single HTML file) and free of personal information.

## Local preview

```
python scripts/build_index.py
open _site/index.html        # macOS; on Linux: xdg-open
```

## License

MIT — see [LICENSE](LICENSE).
