#!/usr/bin/env python3
"""Build the cheat-sheet site into _site/.

Scans sheets/*.html, pulls each page's <title> and subtitle line, and writes
an index.html linking to them all. Run by the GitHub Actions workflow on every
push (and runnable locally: `python scripts/build_index.py`).
"""

import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "sheets"
SITE = ROOT / "_site"

CARD = """  <a class="card" href="sheets/{fname}">
    <h3>{title}</h3>
    <p>{sub}</p>
  </a>"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cheat Sheets</title>
<style>
  :root{{
    --bg:#0f1117; --card:#171a21; --ink:#e6e8ee; --muted:#9aa3b2;
    --accent:#7aa2f7; --border:#262b36;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    line-height:1.5;padding:40px 18px 60px;}}
  .wrap{{max-width:900px;margin:0 auto;}}
  h1{{font-size:28px;margin:0 0 6px;}}
  .sub{{color:var(--muted);font-size:14px;margin:0 0 28px;}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;}}
  .card{{display:block;background:var(--card);border:1px solid var(--border);
    border-radius:10px;padding:18px;text-decoration:none;color:var(--ink);
    transition:border-color .15s;}}
  .card:hover{{border-color:var(--accent);}}
  .card h3{{margin:0 0 6px;font-size:16px;color:var(--accent);}}
  .card p{{margin:0;font-size:13px;color:var(--muted);}}
  .foot{{color:var(--muted);font-size:12px;margin-top:36px;
    border-top:1px solid var(--border);padding-top:12px;}}
  a{{color:var(--accent);}}
</style>
</head>
<body>
<div class="wrap">
<h1>Cheat Sheets</h1>
<p class="sub">Quick references for dev tooling. Index auto-generated — add an HTML file to <code>sheets/</code> and push.</p>
<div class="grid">
{cards}
</div>
<p class="foot">Built {today} · <a href="https://github.com/{repo}">source on GitHub</a> — PRs welcome.</p>
</div>
</body>
</html>
"""


def extract(html: str, pattern: str, default: str) -> str:
    m = re.search(pattern, html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else default


def main() -> None:
    import os

    repo = os.environ.get("GITHUB_REPOSITORY", "yourname/cheatsheets")

    # Overwrite in place (no rmtree: some sandboxed filesystems forbid unlink,
    # and stale files are pruned below instead).
    (SITE / "sheets").mkdir(parents=True, exist_ok=True)
    wanted = {f.name for f in SHEETS.glob("*.html")}
    for old in (SITE / "sheets").glob("*.html"):
        if old.name not in wanted:
            try:
                old.unlink()
            except OSError:
                print(f"warning: could not remove stale {old}")

    cards = []
    for f in sorted(SHEETS.glob("*.html")):
        html = f.read_text(encoding="utf-8")
        title = extract(html, r"<title>(.*?)</title>", f.stem)
        # subtitle: first <p class="sub">, strip tags, keep it short
        sub = extract(html, r'<p class="sub">(.*?)</p>', "")
        sub = re.sub(r"<[^>]+>", "", sub)
        sub = sub.split("·")[0].strip()  # keep only the descriptive part
        cards.append(CARD.format(fname=f.name, title=title, sub=sub))
        shutil.copy2(f, SITE / "sheets" / f.name)

    (SITE / "index.html").write_text(
        PAGE.format(cards="\n".join(cards), today=date.today().isoformat(), repo=repo),
        encoding="utf-8",
    )
    print(f"Built _site/ with {len(cards)} sheet(s).")


if __name__ == "__main__":
    main()
