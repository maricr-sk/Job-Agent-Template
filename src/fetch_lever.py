"""Pull open postings from a company's public Lever job board.

No API key needed. Docs: https://github.com/lever/postings-api
"""
import requests

BASE = "https://api.lever.co/v0/postings/{token}"


def fetch(token: str) -> list[dict]:
    url = BASE.format(token=token) + "?mode=json"
    try:
        resp = requests.get(url, timeout=15)
    except requests.RequestException as e:
        print(f"  [lever:{token}] request failed: {e}")
        return []

    if resp.status_code != 200:
        print(f"  [lever:{token}] HTTP {resp.status_code} — skipping (bad token or no board)")
        return []

    jobs = resp.json()
    out = []
    for j in jobs:
        categories = j.get("categories", {}) or {}
        desc = j.get("descriptionPlain", "") or j.get("description", "") or ""
        out.append({
            "source": "lever",
            "company": token,
            "title": j.get("text", ""),
            "location": categories.get("location", ""),
            "description": desc,
            "url": j.get("hostedUrl", ""),
            "updated_at": j.get("createdAt", ""),
        })
    print(f"  [lever:{token}] {len(out)} postings")
    return out
