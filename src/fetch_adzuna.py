"""Pull postings from Adzuna's aggregator API (covers boards Greenhouse/
Lever/Ashby don't, e.g. companies on Workday, LinkedIn-posted roles, etc.).

Needs a free app_id/app_key from https://developer.adzuna.com/ (~30 sec
signup, no cost for this volume). Set as env vars:
    ADZUNA_APP_ID, ADZUNA_APP_KEY
If unset, this fetcher is skipped rather than erroring the whole run.

Docs: https://developer.adzuna.com/docs/search
"""
import os
import requests

BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


def fetch(queries: list[str], country: str = "us", max_pages: int = 2, results_per_page: int = 50) -> list[dict]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("  [adzuna] ADZUNA_APP_ID/ADZUNA_APP_KEY not set — skipping")
        return []

    out = []
    for query in queries:
        for page in range(1, max_pages + 1):
            url = BASE.format(country=country, page=page)
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "results_per_page": results_per_page,
                "what": query,
                "content-type": "application/json",
            }
            try:
                resp = requests.get(url, params=params, timeout=15)
            except requests.RequestException as e:
                print(f"  [adzuna:{query}] request failed: {e}")
                break

            if resp.status_code != 200:
                print(f"  [adzuna:{query}] HTTP {resp.status_code} — stopping this query")
                break

            results = resp.json().get("results", [])
            if not results:
                break

            for j in results:
                out.append({
                    "source": "adzuna",
                    "company": (j.get("company") or {}).get("display_name", "Unknown"),
                    "title": j.get("title", ""),
                    "location": (j.get("location") or {}).get("display_name", ""),
                    "description": j.get("description", "") or "",
                    "url": j.get("redirect_url", ""),
                    "updated_at": j.get("created", ""),
                    "salary_min": j.get("salary_min"),
                    "salary_max": j.get("salary_max"),
                })
    print(f"  [adzuna] {len(out)} postings across {len(queries)} queries")
    return out
