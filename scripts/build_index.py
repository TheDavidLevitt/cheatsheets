#!/usr/bin/env python3
"""Build the cheat-sheet site into _site/.

Scans sheets/*.html and writes an index.html with a live full-text search bar
and three ordered columns (Architecture / Tools / Languages). Entries in
LAYOUT control column + order; "@slug" entries place a GROUPS hub card
(one card on the home page → generated hub page, e.g. gcp.html).
BLURBS supplies the one-line description under each card title.

Run by GitHub Actions on every push, or locally:
`python scripts/build_index.py`.

Adding a sheet: drop the HTML in sheets/, then add a LAYOUT entry (else it
lands at the bottom of Tools) and a BLURB (else the sheet's subtitle is used).
"""

import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "sheets"
SITE = ROOT / "_site"

# Column order on the page; entries within each list are display order.
# Plain entries are filenames in sheets/; "@slug" places a GROUPS hub card.
LAYOUT = {
    "Architecture": [
        "hardware_cheatsheet.html",
        "system_architecture_cheatsheet.html",
        "networking_cheatsheet.html",
        "encryption_cheatsheet.html",
        "authentication_cheatsheet.html",
        "ssh_cheatsheet.html",
        "cloud_comparison_cheatsheet.html",
        "@gcp",
        "azure_cheatsheet.html",
    ],
    "Tools": [
        "vscode_cheatsheet.html",
        "git_cheatsheet.html",
        "github_cheatsheet.html",
        "vim_cheatsheet.html",
        "homebrew_cheatsheet.html",
        "claude_api_cheatsheet.html",
        "terraform_cheatsheet.html",
        "obsidian_cheatsheet.html",
        "excel_functions_cheatsheet.html",
    ],
    "Languages": [
        "bash_zsh_cheatsheet.html",
        "powershell_cheatsheet.html",
        "python_cheatsheet.html",
        "python_environments_cheatsheet.html",
        "formats_cheatsheet.html",
        "html_cheatsheet.html",
    ],
}

GROUPS = {
    "gcp": {
        "name": "GCP — Google Cloud",
        "blurb": "Google's cloud, drilled in: IAM, compute, databases, analytics.",
        "files": [
            "gcp_iam_auth_cheatsheet.html",
            "gcp_compute_cheatsheet.html",
            "gcp_databases_storage_cheatsheet.html",
            "gcp_data_analytics_cheatsheet.html",
            "gcp_networking_cheatsheet.html",
        ],
    },
}

# One line under each title: what it is / what it's for. Light where obvious.
BLURBS = {
    # Architecture
    "hardware_cheatsheet.html": "What the computer is made of — and why AI wants all the RAM.",
    "system_architecture_cheatsheet.html": "Everything between the silicon and your script: languages, kernels, containers.",
    "networking_cheatsheet.html": "How the internet works, packet by packet.",
    "encryption_cheatsheet.html": "When will your personal data be public?",
    "authentication_cheatsheet.html": "OAuth, tokens, and why apps stopped asking for your password.",
    "ssh_cheatsheet.html": "A terminal on someone else's computer, safely.",
    "cloud_comparison_cheatsheet.html": "Same Lego bricks, three sticker sheets.",
    "azure_cheatsheet.html": "Microsoft's cloud — and the corporate data maze (SharePoint, Dataverse, Fabric).",
    # Tools
    "vscode_cheatsheet.html": "The editor. Plus Jupyter without the browser.",
    "git_cheatsheet.html": "Version management.",
    "github_cheatsheet.html": "Where your code meets everyone else's.",
    "vim_cheatsheet.html": "The editor you didn't open on purpose.",
    "homebrew_cheatsheet.html": "Install programs from your CLI.",
    "claude_api_cheatsheet.html": "Talk to Claude from code instead of a chat box.",
    "terraform_cheatsheet.html": "Build cloud infrastructure by writing it down.",
    "obsidian_cheatsheet.html": "Plain-text notes that link to each other.",
    "excel_functions_cheatsheet.html": "LAMBDA, CUBEVALUE, DATEDIF, EOMONTH — the greatest hits.",
    # Languages
    "bash_zsh_cheatsheet.html": "The terminal's native language; the glue holding everything together.",
    "powershell_cheatsheet.html": "Bash for Windows — except it pipes objects, not text.",
    "python_cheatsheet.html": "The default language for data, science, and AI.",
    "python_environments_cheatsheet.html": "Keep one project's packages from poisoning another's.",
    "formats_cheatsheet.html": "JSON, REST, YAML — how programs talk to each other.",
    "html_cheatsheet.html": "The structure of every web page.",
    # GCP members (shown on the hub page)
    "gcp_iam_auth_cheatsheet.html": "Who may do what — permissions, roles, and the two credential stores.",
    "gcp_compute_cheatsheet.html": "VMs to serverless: the managed-vs-control spectrum.",
    "gcp_databases_storage_cheatsheet.html": "Which data goes in which box (and what it costs).",
    "gcp_data_analytics_cheatsheet.html": "Big data: from MapReduce lore to BigQuery bills.",
    "gcp_networking_cheatsheet.html": "VPCs, subnets, firewall rules — the private roads between your machines.",
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
    sub = BLURBS.get(f.name)
    if not sub:
        sub = extract(html, r'<p class="sub">(.*?)</p>', "")
        sub = re.sub(r"<[^>]+>", "", sub).split("·")[0].strip()
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

    # Build a card for every sheet; copy into the site.
    cards: dict[str, str] = {}
    searches: dict[str, str] = {}
    content_index: dict[str, str] = {}
    for f in sorted(SHEETS.glob("*.html")):
        shutil.copy2(f, SITE / "sheets" / f.name)
        card, search, words = sheet_card(f, f"sheets/{f.name}")
        cards[f.name], searches[f.name], content_index[f.name] = card, search, words

    # Hub pages + hub cards for groups.
    grouped_files: set[str] = set()
    hub_cards: dict[str, str] = {}
    for slug, g in GROUPS.items():
        members = [m for m in g["files"] if m in cards]
        if not members:
            continue
        grouped_files.update(members)
        (SITE / f"{slug}.html").write_text(
            HUB.format(css=CSS, name=g["name"], blurb=g["blurb"],
                       cards="\n".join(cards[m] for m in members),
                       today=today, repo=repo),
            encoding="utf-8",
        )
        content_index[slug] = " ".join(content_index.pop(m, "") for m in members)
        search = (g["name"] + " " + g["blurb"] + " "
                  + " ".join(searches[m] for m in members)).lower().replace('"', "")
        hub_cards[slug] = CARD.format(
            href=f"{slug}.html",
            title=f'{g["name"]}<span class="badge">{len(members)} sheets</span>',
            sub=g["blurb"], search=search, key=slug,
        )

    # Assemble columns per LAYOUT; unknown sheets fall to the end of Tools.
    placed: set[str] = set()
    by_col: dict[str, list[str]] = {}
    for col, entries in LAYOUT.items():
        out = []
        for e in entries:
            if e.startswith("@"):
                if e[1:] in hub_cards:
                    out.append(hub_cards[e[1:]])
                    placed.add(e[1:])
            elif e in cards and e not in grouped_files:
                out.append(cards[e])
                placed.add(e)
        by_col[col] = out
    for name, card in cards.items():
        if name not in placed and name not in grouped_files:
            by_col["Tools"].append(card)

    columns = "\n".join(
        COLUMN.format(cid=c.lower(), cname=c, cards="\n".join(by_col[c]) or "")
        for c in LAYOUT
    )
    (SITE / "index.html").write_text(
        PAGE.format(css=CSS, columns=columns, today=today, repo=repo,
                    content_index=json.dumps(content_index, separators=(",", ":"))),
        encoding="utf-8",
    )
    n = len(cards)
    print(f"Built _site/ with {n} sheet(s); {len(hub_cards)} group hub(s).")


if __name__ == "__main__":
    main()
