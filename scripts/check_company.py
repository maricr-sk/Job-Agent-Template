"""Run locally (not in the sandbox this was built in — it needs open
network access) to find which ATS a company uses and whether your slug
guess is right.

Usage:
    python scripts/check_company.py assort-health
    python scripts/check_company.py assorthealth

Try a few reasonable slug variants (with/without hyphens, abbreviations)
until one hits. Whichever prints "FOUND", copy that exact token into
config/companies.yaml under the matching ATS.
"""
import sys
import requests

CHECKS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_company.py <slug-guess>")
        sys.exit(1)

    slug = sys.argv[1]
    found_any = False
    for ats, url_template in CHECKS.items():
        url = url_template.format(slug=slug)
        try:
            resp = requests.get(url, timeout=10)
        except requests.RequestException as e:
            print(f"{ats:12} ERROR ({e})")
            continue

        if resp.status_code == 200:
            count = len(resp.json().get("jobs", resp.json()) if isinstance(resp.json(), dict) else resp.json())
            print(f"{ats:12} FOUND — {count} postings. Add '{slug}' under '{ats}:' in config/companies.yaml")
            found_any = True
        else:
            print(f"{ats:12} not this one (HTTP {resp.status_code})")

    if not found_any:
        print(f"\nNo match for '{slug}'. Try another slug variant, or check if this company"
              f" uses Workday/SmartRecruiters instead (not covered by this project yet).")


if __name__ == "__main__":
    main()
