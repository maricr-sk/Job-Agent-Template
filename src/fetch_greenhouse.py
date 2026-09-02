"""Pull open postings from a company's public Greenhouse job board.

No API key needed. Docs: https://developers.greenhouse.io/job-board.html
"""
import requests

BASE = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(token: str) -> list[dict]:
    url = BASE.format(token=token) + "?content=true"
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"  [greenhouse:{token}] request failed: {e}")
        return []

    if resp.status_code != 200:
        print(f"  [greenhouse:{token}] HTTP {resp.status_code} — skipping (bad token or no board)")
        return []

    jobs = resp.json().get("jobs", [])
    out = []
    for j in jobs:
        out.append({
            "source": "greenhouse",
            "company": token,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "description": j.get("content", "") or "",
            "url": j.get("absolute_url", ""),
            "updated_at": j.get("updated_at", ""),
        })
    print(f"  [greenhouse:{token}] {len(out)} postings")
    return out
