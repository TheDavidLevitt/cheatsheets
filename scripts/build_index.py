#!/usr/bin/env python3
"""Build the cheat-sheet site into _site/.

Scans sheets/*.html, pulls each page's <title> and subtitle line, and writes
an index.html with a live search bar and three category columns
(Languages / Tools / Architecture). Sheets listed in GROUPS are nested behind
a single card that links to a generated hub page (e.g. gcp.html).
Run by the GitHub Actions workflow on every push (and locally:
`python scripts/build_index.py`).

To place a new sheet, add its filename to CATEGORIES (unknown sheets land in
"Tools") or to a GROUPS entry.
"""

import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "sheets"
SITE = ROOT / "_site"

COLUMNS = ["Languages", "Tools", "Architecture"]

CATEGORIES = {
    # Languages — syntax you read & write
    "python_cheatsheet.html": "Languages",
    "html_cheatsheet.html": "Languages",
    "bash_zsh_cheatsheet.html": "Languages",
    "powershell_cheatsheet.html": "Languages",
    "formats_cheatsheet.html": "Languages",
    # Tools — software you operate
    "git_cheatsheet.html": "Tools",
    "github_cheatsheet.html": "Tools",
    "vim_cheatsheet.html": "Tools",
    "vscode_cheatsheet.html": "Tools",
    "homebrew_cheatsheet.html": "Tools",
    "obsidian_cheatsheet.html": "Tools",
    "excel_functions_cheatsheet.html": "Tools",
    "claude_api_cheatsheet.html": "Tools",
    "terraform_cheatsheet.html": "Tools",
    "python_environments_cheatsheet.html": "Tools",
    # Architecture — how systems are put together
    "cloud_comparison_cheatsheet.html": "Architecture",
    "azure_cheatsheet.html": "Architecture",
    "hardware_cheatsheet.html": "Architecture",
    "system_architecture_cheatsheet.html": "Architecture",
    "networking_cheatsheet.html": "Architecture",
    "ssh_cheatsheet.html": "Architecture",
    "encryption_cheatsheet.html": "Architecture",
}

# Nested collections: one card on the home page → a hub page listing members.
GROUPS = {
    "gcp": {
        "name": "GCP — Google Cloud",
        "category": "Architecture",
        "blurb": "Four drill-ins: IAM & auth, compute, databases & storage, data analytics.",
        "files": [
            "gcp_iam_auth_cheatsheet.html",
            "gcp_compute_cheatsheet.html",
            "gcp_databases_storage_cheatsheet.html",
            "gcp_data_analytics_cheatsheet.html",
        ],
    },
}

CARD = """      <a class="card" href="{href}" data-search="{search}" data-key="{key}">
        <h3>{title}</h3>
        <p>{sub}</p>
      </a>"""

COLUMN = """  <section class="col" id="{cid}">
    <h2>{cname}</h2>
{cards}
    <p class="empty" hidden>No matches.</p>
  </section>"""

CSS = """  :root{
    --bg:#0f1117; --card:#171a21; --ink:#e6e8ee; --muted:#9aa3b2;
    --accent:#7aa2f7; --border:#262b36; --code:#1d2230;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
    line-height:1.5;padding:40px 18px 60px;}
  .wrap{max-width:1200px;margin:0 auto;}
  h1{font-size:28px;margin:0 0 6px;}
  .sub{color:var(--muted);font-size:14px;margin:0 0 18px;}
  #search{width:100%;max-width:520px;display:block;margin:0 0 28px;
    background:var(--code);border:1px solid var(--border);border-radius:8px;
    color:var(--ink);font-size:15px;padding:10px 14px;outline:none;}
  #search:focus{border-color:var(--accent);}
  .cols{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;}
  @media (max-width:900px){.cols{grid-template-columns:1fr;}}
  .col h2{font-size:15px;letter-spacing:.05em;text-transform:uppercase;
    color:var(--accent);border-bottom:1px solid var(--border);
    padding-bottom:6px;margin:0 0 14px;}
  .single{max-width:560px;}
  .card{display:block;background:var(--card);border:1px solid var(--border);
    border-radius:10px;padding:14px 16px;margin-bottom:12px;
    text-decoration:none;color:var(--ink);transition:border-color .15s;}
  .card:hover{border-color:var(--accent);}
  .card.hit{border-color:var(--accent);}
  .card h3{margin:0 0 5px;font-size:15px;color:var(--accent);}
  .card p{margin:0;font-size:12.5px;color:var(--muted);}
  .badge{display:inline-block;font-size:10.5px;text-transform:uppercase;
    letter-spacing:.05em;color:var(--muted);border:1px solid var(--border);
    border-radius:5px;padding:0 6px;margin-left:8px;vertical-align:2px;}
  .empty{color:var(--muted);font-size:13px;}
  .back{display:inline-block;margin:0 0 20px;color:var(--accent);font-size:14px;}
  .foot{color:var(--muted);font-size:12px;margin-top:36px;
    border-top:1px solid var(--border);padding-top:12px;}
  a{color:var(--accent);}"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cheat Sheets</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
<h1>Cheat Sheets</h1>
<p class="sub">Quick references for dev tooling. Index auto-generated — add an HTML file to <code>sheets/</code> and push.</p>
<input id="search" type="search" placeholder="Search sheets…  (e.g. git, pandas, DNS)" autofocus>
<div class="cols">
{columns}
</div>
<p class="foot">Built {today} · <a href="https://github.com/{repo}">source on GitHub</a> — PRs welcome.</p>
</div>
<script>
  // Full-text word index per sheet, generated at build time.
  const CONTENT = {content_index};
  const q = document.getElementById('search');
  q.addEventListener('input', () => {{
    const needle = q.value.trim().toLowerCase();
    document.querySelectorAll('.col').forEach(col => {{
      let visible = 0;
      col.querySelectorAll('.card').forEach(card => {{
        const inMeta = card.dataset.search.includes(needle);
        const inBody = (CONTENT[card.dataset.key] || '').includes(needle);
        const hit = !needle || inMeta || inBody;
        card.hidden = !hit;
        card.classList.toggle('hit', !!needle && hit);
        if (hit) visible++;
      }});
      col.querySelector('.empty').hidden = visible > 0;
    }});
  }});
</script>
</body>
</html>
"""

HUB = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap single">
<a class="back" href="index.html">&larr; All cheat sheets</a>
<h1>{name}</h1>
<p class="sub">{blurb}</p>
{cards}
<p class="foot">Built {today} · <a href="https://github.com/{repo}">source on GitHub</a></p>
</div>
</body>
</html>
"""


def extract(html: str, pattern: str, default: str) -> str:
    m = re.search(pattern, html, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else default


def clean_title(title: str) -> str:
    """Drop the repetitive 'Cheat Sheet' suffix/infix from display titles."""
    t = re.sub(r"\s*Cheat\s*Sheet\s*", " ", title, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t).strip(" ·-—–")
    return t or title


def body_words(html: str) -> str:
    """Visible text of a sheet, reduced to a compact unique-word string."""
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z#0-9]+;", " ", t)
    words = sorted(set(re.findall(r"[a-z0-9][a-z0-9+#./_-]{2,}", t.lower())))
    return " ".join(words)


def sheet_card(f: Path, href: str) -> tuple[str, str, str]:
    """Return (card html, searchable meta, body word index) for one sheet."""
    html = f.read_text(encoding="utf-8")
    title = clean_title(extract(html, r"<title>(.*?)</title>", f.stem))
    sub = extract(html, r'<p class="sub">(.*?)</p>', "")
    sub = re.sub(r"<[^>]+>", "", sub)
    sub = sub.split("·")[0].strip()
    search = f"{title} {sub} {f.stem}".lower().replace('"', "")
    card = CARD.format(href=href, title=title, sub=sub, search=search, key=f.name)
    return card, search, body_words(html)


def main() -> None:
    import os

    repo = os.environ.get("GITHUB_REPOSITORY", "yourname/cheatsheets")
    today = date.today().isoformat()

    # Overwrite in place (no rmtree: some sandboxed filesystems forbid unlink).
    (SITE / "sheets").mkdir(parents=True, exist_ok=True)
    wanted = {f.name for f in SHEETS.glob("*.html")}
    for old in (SITE / "sheets").glob("*.html"):
        if old.name not in wanted:
            try:
                old.unlink()
            except OSError:
                print(f"warning: could not remove stale {old}")

    grouped = {fname: slug for slug, g in GROUPS.items() for fname in g["files"]}
    by_col: dict[str, list[str]] = {c: [] for c in COLUMNS}
    group_cards: dict[str, list[str]] = {slug: [] for slug in GROUPS}
    group_search: dict[str, list[str]] = {slug: [] for slug in GROUPS}
    content_index: dict[str, str] = {}
    n = 0

    for f in sorted(SHEETS.glob("*.html")):
        shutil.copy2(f, SITE / "sheets" / f.name)
        n += 1
        card, search, words = sheet_card(f, f"sheets/{f.name}")
        if f.name in grouped:
            slug = grouped[f.name]
            group_cards[slug].append(card)
            group_search[slug].append(search)
            content_index[slug] = content_index.get(slug, "") + " " + words
        else:
            by_col[CATEGORIES.get(f.name, "Tools")].append(card)
            content_index[f.name] = words

    # One card per group on the home page; hub page holds the members.
    for slug, g in GROUPS.items():
        if not group_cards[slug]:
            continue
        (SITE / f"{slug}.html").write_text(
            HUB.format(css=CSS, name=g["name"], blurb=g["blurb"],
                       cards="\n".join(group_cards[slug]), today=today, repo=repo),
            encoding="utf-8",
        )
        search = f'{g["name"]} {g["blurb"]} ' + " ".join(group_search[slug])
        by_col[g["category"]].append(
            CARD.format(href=f"{slug}.html",
                        title=f'{g["name"]}<span class="badge">{len(group_cards[slug])} sheets</span>',
                        sub=g["blurb"], search=search.lower().replace('"', ""),
                        key=slug)
        )

    import json

    columns = "\n".join(
        COLUMN.format(cid=c.lower(), cname=c, cards="\n".join(by_col[c]) or "")
        for c in COLUMNS
    )
    (SITE / "index.html").write_text(
        PAGE.format(css=CSS, columns=columns, today=today, repo=repo,
                    content_index=json.dumps(content_index, separators=(",", ":"))),
        encoding="utf-8",
    )
    print(f"Built _site/ with {n} sheet(s); {len(GROUPS)} group hub(s).")


if __name__ == "__main__":
    main()
