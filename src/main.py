"""Daily entry point: fetch from every configured source, score against
the profile, and write docs/jobs.json for the dashboard to read.

Run locally:   python src/main.py
Run in CI:     see .github/workflows/daily-job-scan.yml
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.profile import PROFILE as BASE_PROFILE
from src import fetch_greenhouse, fetch_lever, fetch_ashby, fetch_adzuna, fetch_github_lists
from src.scorer import rank_jobs

# Search terms for the Adzuna aggregator — built from my target roles
# and priority topics so it isn't just "software engineer" noise.

# Some FAANG/big-tech AI & software roles, entry-level focused. Adzuna has
# no direct "employer" filter, so company names go straight in the
# search text — it's a soft signal (surfaces postings mentioning the
# company, not a guaranteed employer match), but it's the only lever
# Adzuna gives us since Google/Meta/Amazon/Apple/Netflix/Microsoft run
# their own ATS and aren't reachable via the Greenhouse/Lever/Ashby
# fetchers at all.
ADZUNA_QUERIES = [
    "technical program manager",
    "product manager",
    "AI product manager",
    "forward deployed engineer",
    "software engineer new grad Google",
    "software engineer new grad Meta",
    "software engineer new grad Microsoft",
    "machine learning engineer entry level",
    "AI research engineer entry level",
]


def load_companies():
    with open(ROOT / "config" / "companies.yaml") as f:
        return yaml.safe_load(f)


def load_profile() -> dict:
    """Starts from the public template (config/profile.py) and merges in
    a private override if PROFILE_OVERRIDE_JSON is set — a repo secret
    holding your real name/skills/salary floor/etc. as a JSON object.
    This is how the repo stays public and generic while your actual
    targeting data never gets committed anywhere. See README."""
    profile = dict(BASE_PROFILE)
    raw = os.environ.get("PROFILE_OVERRIDE_JSON")
    if not raw:
        return profile
    try:
        overrides = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"PROFILE_OVERRIDE_JSON is set but not valid JSON ({e}) — using the public template instead.")
        return profile
    profile.update(overrides)
    print("Loaded private profile override from PROFILE_OVERRIDE_JSON.")
    return profile


def main():
    profile = load_profile()
    companies = load_companies()
    all_jobs = []

    print("Fetching Greenhouse boards...")
    for token in companies.get("greenhouse", []) or []:
        all_jobs.extend(fetch_greenhouse.fetch(token))

    print("Fetching Lever boards...")
    for token in companies.get("lever", []) or []:
        all_jobs.extend(fetch_lever.fetch(token))

    print("Fetching Ashby boards...")
    for token in companies.get("ashby", []) or []:
        all_jobs.extend(fetch_ashby.fetch(token))

    print("Fetching Adzuna...")
    all_jobs.extend(fetch_adzuna.fetch(ADZUNA_QUERIES))

    print("Fetching speedyapply new-grad list...")
    all_jobs.extend(fetch_github_lists.fetch_speedyapply())

    print("Fetching Simplify new-grad list...")
    all_jobs.extend(fetch_github_lists.fetch_simplify_new_grad())

    print(f"\nTotal raw postings: {len(all_jobs)}")
    ranked = rank_jobs(all_jobs, profile)
    print(f"After dedupe + exclusions: {len(ranked)}")

    threshold = profile.get("min_score_threshold", 0)
    ranked = [j for j in ranked if j["score"] >= threshold]
    print(f"After {threshold}+ score threshold: {len(ranked)}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile_name": profile["name"],
        "total_jobs": len(ranked),
        "jobs": ranked,
    }

    out_path = ROOT / "docs" / "jobs.json"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
