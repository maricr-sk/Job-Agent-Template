"""
Candidate profile used by src/scorer.py to score job postings.

This file is the PUBLIC TEMPLATE — it ships with generic example values so
the repo is safe to keep public. Your real name, salary floor, and target
list should NOT be edited into this file. Instead, set them as a repo
secret called PROFILE_OVERRIDE_JSON (see README: "Keeping your real
profile private"), and main.py merges it in at runtime — your actual
values never get committed anywhere.

Feel free to still edit the shape of things here (add new profile keys,
change scoring-relevant structure) — just keep the VALUES generic.
"""

PROFILE = {
    "name": "Your Name",

    # Example skills — replace via your private override, not here.
    "skills": [
        "python", "sql", "react", "javascript", "aws",
        "machine learning", "data pipelines", "rest api",
    ],

    # Role titles/keywords to target. Weighted higher than plain skill
    # matches when they appear in the job title.
    "target_roles": [
        "software engineer", "forward deployed engineer", "data scientist", 
        "machine learning engineer", "data engineer", "backend engineer",
        "full stack engineer", "product engineer"
    ],

    # Topic areas to boost heavily. Keep these specific — very common
    # words like "tech" or "software" will match nearly every posting and
    # erase the whole point of this list (see README).
    "priority_topics": [
        "machine learning", "generative ai", "distributed systems",
        "data engineering",
    ],

    # Companies/keywords to exclude outright regardless of score.
    "excluded_companies": [],

    # Soft preferences — don't exclude, just note in scoring rationale.
    "preferred_locations": ["remote", "hybrid", "san francisco", "bay area", "new york", "austin"],
    "avoid_onsite_5_days": True,
    "salary_floor": 80000,

    # Only jobs scoring at or above this make it into the dashboard at all.
    "min_score_threshold": 50,

    # Title terms to deprioritize (not exclude) — useful if you're
    # targeting entry-level and don't want senior/staff/principal roles
    # crowding the top, or vice-versa.
    "deprioritized_title_terms": ["senior", "sr.", "staff", "principal"],
    "senior_title_multiplier": 0.6,

    # Phrases that signal an entry-level/new-grad posting — boosted when
    # found, especially in the title.
    "new_grad_terms": [
        "new grad", "entry level", "entry-level",
        "early career", "recent graduate", "associate", "junior"
    ],

    # A posting requiring at least this many years of experience gets
    # knocked down (not excluded).
    "min_years_deprioritize": 3,
    "years_required_multiplier": 0.6,

    # Recency: a posting gets up to this many points, decaying linearly to
    # 0 by the time it's this many days old.
    "recency_boost_max": 15,
    "recency_boost_window_days": 14,
}
