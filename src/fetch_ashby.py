"""Pull open postings from a company's public Ashby job board.

No API key needed. Docs: https://developers.ashbyhq.com/docs/public-job-board-api
"""
import requests

BASE = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def fetch(token: str) -> list[dict]:
    url = BASE.format(token=token)
    try:
        resp = requests.get(url, timeout=15, params={"includeCompensation": "true"})
    except requests.RequestException as e:
        print(f"  [ashby:{token}] request failed: {e}")
        return []

    if resp.status_code != 200:
        print(f"  [ashby:{token}] HTTP {resp.status_code} — skipping (bad token or no board)")
        return []

    jobs = resp.json().get("jobs", [])
    out = []
    for j in jobs:
        out.append({
            "source": "ashby",
            "company": token,
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "description": j.get("descriptionPlain", "") or "",
            "url": j.get("jobUrl", ""),
            "updated_at": j.get("publishedAt", ""),
        })
    print(f"  [ashby:{token}] {len(out)} postings")
    return out
