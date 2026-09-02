# Job-Agent-Template
Agent that uses ur personalized values to search job DBs like Adzuna, github repos, and greenhouse to aggregate them in one place (hopefully more efficiently than LinkedIn)

# Job Agent — Setup

Fill in the blanks, in order. Takes about 15 minutes.

## 1. Push to GitHub

cd job-agent
git init
git add .
git commit -m "Initial job agent"
gh repo create <repo_name> --public --source=. --push

## 2. Get a free Adzuna API key
Sign up: https://developer.adzuna.com/

app_id: ______________
app_key: ______________


## 3. Add repo secrets
Settings → Secrets and variables → Actions → New repository secret:

ADZUNA_APP_ID = ______________ (from step 2)
ADZUNA_APP_KEY = ______________ (from step 2)
PROFILE_OVERRIDE_JSON = ______________ (the JSON from step 3)

## 4. Fill in your real profile (kept private)
Copy this, fill in your values, keep it somewhere for step 4 — do not
commit it to the repo:
```json
{
  "name": "______________",
  "salary_floor": ______________,
  "excluded_companies": [______________],
  "preferred_locations": [______________]
}
```
Any key from `config/profile.py` can go in here (skills, target_roles,
priority_topics, etc.) — only include what you want to override.


## 5. Enable GitHub Pages
Settings → Pages → Source: **Deploy from a branch** → Branch: **main**,
folder: **/docs** → Save.

Dashboard URL: https://.github.io//


## 6. Run it once
Actions tab → **Daily job scan** → **Run workflow**. Wait ~30 sec, then
refresh the dashboard URL — it should have real data.

---

That's it — it reruns on its own daily. To change the time, edit the
cron line in `.github/workflows/daily-job-scan.yml`.