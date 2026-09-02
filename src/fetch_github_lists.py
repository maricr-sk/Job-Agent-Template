"""Pull entries from two community-maintained "new grad job list" GitHub
repos. Both are plain public files fetched via raw.githubusercontent.com —
no scraping, no auth, just reading a public markdown file, updated daily
by their maintainers and contributors.

  - speedyapply/2027-SWE-College-Jobs — NEW_GRAD_USA.md, a markdown
    pipe-table format (FAANG+ / Quant / Other sections).
  - SimplifyJobs/New-Grad-Positions — README.md, an HTML-table-in-markdown
    format (Software Engineering / Product Management / Data Science &
    ML / Quant / Hardware sections).

Both list only entry-level/new-grad roles by nature, and both include an
"Age" column (days since posted), which is where posted_days_ago comes
from for these two sources — the closest thing to true "date added" data
in this whole pipeline.
"""
import html
import re
from datetime import datetime, timezone

import requests

SPEEDYAPPLY_URL = "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/NEW_GRAD_USA.md"
SIMPLIFY_CANDIDATE_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md",
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/main/README.md",
]


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _first_href(s: str) -> str:
    m = re.search(r'href="([^"]+)"', s)
    return m.group(1) if m else ""


def _parse_age(s: str):
    s = _strip_tags(s).strip().lower()
    m = re.match(r"(\d+)\s*(d|mo|h)?$", s)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2) or "d"
    if unit == "mo":
        return num * 30
    if unit == "h":
        return 0
    return num


def fetch_speedyapply() -> list[dict]:
    try:
        resp = requests.get(SPEEDYAPPLY_URL, timeout=20)
    except requests.RequestException as e:
        print(f"  [speedyapply] request failed: {e}")
        return []
    if resp.status_code != 200:
        print(f"  [speedyapply] HTTP {resp.status_code} — skipping")
        return []

    text = resp.text
    out = []
    # Every table block sits between a "..._START" and "..._END" comment,
    # regardless of category (FAANG/Quant/generic "Other").
    for block in re.findall(r"<!-- TABLE\w*_START -->(.*?)<!-- TABLE\w*_END -->", text, re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if not line.startswith("|") or "---" in line or line.startswith("| Company"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) not in (5, 6):
                continue
            if len(cells) == 6:
                company_cell, position, location, salary, posting_cell, age_cell = cells
            else:
                company_cell, position, location, posting_cell, age_cell = cells
                salary = ""

            out.append({
                "source": "speedyapply",
                "company": _strip_tags(company_cell),
                "title": _strip_tags(position),
                "location": _strip_tags(location),
                "description": f"New grad listing. {salary}".strip(),
                "url": _first_href(posting_cell) or _first_href(company_cell),
                "posted_days_ago": _parse_age(age_cell),
                "salary_raw": salary,
            })
    print(f"  [speedyapply] {len(out)} postings")
    return out


def fetch_simplify_new_grad() -> list[dict]:
    text = None
    for url in SIMPLIFY_CANDIDATE_URLS:
        try:
            resp = requests.get(url, timeout=20)
        except requests.RequestException as e:
            print(f"  [simplify-newgrad] request failed for {url}: {e}")
            continue
        if resp.status_code == 200:
            text = resp.text
            break
        print(f"  [simplify-newgrad] HTTP {resp.status_code} for {url}")

    if text is None:
        print("  [simplify-newgrad] no working branch found — skipping "
              "(repo may have renamed its default branch; update SIMPLIFY_CANDIDATE_URLS)")
        return []

    # Tag each row with the category header it falls under, so scoring can
    # see "Product Management" vs "Software Engineering" etc.
    headings = [(m.start(), _strip_tags(m.group(1)))
                for m in re.finditer(r"^## (.+)$", text, re.MULTILINE)
                if "legend" not in m.group(1).lower()]

    def category_for(pos: int) -> str:
        cat = "General"
        for h_pos, h_title in headings:
            if h_pos <= pos:
                cat = h_title
            else:
                break
        return cat

    out = []
    last_company = ""
    for m in re.finditer(r"<tr>(.*?)</tr>", text, re.DOTALL):
        row_html = m.group(1)
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL)
        if len(cells) < 4:
            continue

        company_text = _strip_tags(cells[0])
        if company_text in ("↳", "") :
            company = last_company
        else:
            company = company_text
            last_company = company

        title = _strip_tags(cells[1]) if len(cells) > 1 else ""
        location = _strip_tags(cells[2]) if len(cells) > 2 else ""
        posting_cell = cells[3] if len(cells) > 3 else ""
        age_cell = cells[4] if len(cells) > 4 else ""

        if not title or not company:
            continue

        out.append({
            "source": "simplify-newgrad",
            "company": company,
            "title": title,
            "location": location,
            "description": f"New grad listing. Category: {category_for(m.start())}",
            "url": _first_href(posting_cell),
            "posted_days_ago": _parse_age(age_cell),
        })
    print(f"  [simplify-newgrad] {len(out)} postings")
    return out
