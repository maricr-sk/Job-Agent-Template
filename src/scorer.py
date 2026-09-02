"""Score and rank fetched job postings against config/profile.py.

Pure keyword/heuristic scoring — no external API or key required. See
README for how to swap in Claude-based scoring later if you want more
nuanced matching than substring counting can give you.
"""
import re
from datetime import datetime, timezone


def _norm(text: str) -> str:
    return (text or "").lower()


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Word-boundary match so short terms like 'c' or 'r' don't match
    inside unrelated words (e.g. 'c' inside 'sales associate')."""
    pattern = r"\b" + re.escape(phrase.lower()) + r"\b"
    return re.search(pattern, haystack) is not None


def _posted_days_ago(job: dict):
    """Returns an int day count if we can figure out how old a posting is,
    else None. speedyapply/simplify-newgrad set this directly at fetch
    time; everything else falls back to parsing 'updated_at' if present."""
    if job.get("posted_days_ago") is not None:
        return job["posted_days_ago"]

    updated_at = job.get("updated_at")
    if not updated_at:
        return None
    try:
        dt = datetime.fromisoformat(str(updated_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - dt).days)
    except (ValueError, TypeError):
        return None


def _required_years(text: str):
    """Finds the largest 'N years [...] experience' figure mentioned, or
    None if no such phrase appears. Deliberately requires the word
    'experience' nearby so it doesn't false-positive on unrelated numbers."""
    matches = re.findall(
        r"(\d{1,2})\+?\s*(?:-\s*\d{1,2}\s*)?years?\s+(?:of\s+)?"
        r"(?:relevant\s+|professional\s+|industry\s+|related\s+)?experience",
        text,
    )
    if not matches:
        return None
    return max(int(m) for m in matches)


def is_excluded(job: dict, profile: dict) -> bool:
    haystack = _norm(job.get("company", "")) + " " + _norm(job.get("title", ""))
    return any(_contains_phrase(haystack, bad) for bad in profile["excluded_companies"])


def score_job(job: dict, profile: dict) -> dict:
    """Returns the job dict with 'score' and 'reasons' added."""
    title = _norm(job.get("title", ""))
    desc = _norm(job.get("description", ""))
    full_text = title + " " + desc

    score = 0.0
    reasons = []

    # Target role match in the title counts most — this is what she's
    # actually applying for, not just adjacent technology.
    role_hits = [r for r in profile["target_roles"] if _contains_phrase(title, r)]
    if role_hits:
        score += 40
        reasons.append(f"title matches target role: {role_hits[0]}")

    # Priority topics (health equity, neuroscience, etc.) — the default
    # boost per job-search preferences.
    topic_hits = [t for t in profile["priority_topics"] if _contains_phrase(full_text, t)]
    if topic_hits:
        score += min(30, 10 * len(set(topic_hits)))
        reasons.append(f"priority topics: {', '.join(sorted(set(topic_hits))[:3])}")

    # Skills overlap.
    skill_hits = [s for s in profile["skills"] if _contains_phrase(full_text, s)]
    if skill_hits:
        score += min(20, 2 * len(set(skill_hits)))
        reasons.append(f"skills: {', '.join(sorted(set(skill_hits))[:5])}")

    # Location preference (soft).
    loc = _norm(job.get("location", ""))
    if any(_contains_phrase(loc, p) for p in profile["preferred_locations"]):
        score += 5
        reasons.append("preferred location")

    # Salary floor, when Adzuna gives us numbers.
    salary_min = job.get("salary_min")
    if salary_min:
        if salary_min >= profile["salary_floor"]:
            score += 5
        else:
            score -= 5
            reasons.append("below stated salary floor")

    # Flag likely 5-days-onsite language without hard-excluding — she
    # said she's declined those but wants to see the option, not lose it.
    if profile.get("avoid_onsite_5_days") and re.search(r"5 days.{0,15}(in.office|onsite)|onsite.{0,10}5 days", full_text):
        reasons.append("mentions 5-day onsite requirement")

    # Boost explicit new-grad/entry-level language — bigger boost when it's
    # in the title, smaller when it's only in the description.
    new_grad_title_hits = [t for t in profile.get("new_grad_terms", []) if _contains_phrase(title, t)]
    new_grad_desc_hits = [t for t in profile.get("new_grad_terms", []) if _contains_phrase(desc, t)]
    if new_grad_title_hits:
        score += 15
        reasons.append(f"new grad/entry-level title: {new_grad_title_hits[0]}")
    elif new_grad_desc_hits:
        score += 8
        reasons.append(f"new grad/entry-level mention: {new_grad_desc_hits[0]}")

    # Recency — linear decay from recency_boost_max at 0 days old down to
    # 0 at recency_boost_window_days old. Only fires when we actually know
    # how old the posting is.
    days_ago = _posted_days_ago(job)
    job["posted_days_ago"] = days_ago
    boost_max = profile.get("recency_boost_max", 0)
    window = profile.get("recency_boost_window_days", 1)
    if days_ago is not None and boost_max:
        recency_boost = max(0, boost_max * (1 - days_ago / window))
        if recency_boost > 0:
            score += recency_boost
            reasons.append(f"posted {days_ago}d ago")

    # Deprioritization happens LAST, as a percentage cut of everything
    # accumulated so far — not a flat subtraction. A flat "-25" barely
    # dents a posting that also picked up recency/new-grad/topic bonuses,
    # which is exactly how senior roles kept surfacing near the top after
    # those bonuses were added. Cutting a percentage keeps the demotion
    # meaningful no matter how high the raw score climbed.
    senior_hits = [t for t in profile.get("deprioritized_title_terms", []) if _contains_phrase(title, t)]
    if senior_hits:
        score *= profile.get("senior_title_multiplier", 0.5)
        reasons.append(f"senior-level title (deprioritized): {senior_hits[0]}")

    min_years = profile.get("min_years_deprioritize")
    required = _required_years(full_text)
    if min_years and required is not None and required >= min_years:
        score *= profile.get("years_required_multiplier", 0.6)
        reasons.append(f"requires {required}+ years experience (deprioritized)")

    # Cap at 100 — the additive bonuses above can sum past it (a strong
    # role/topic/skill match plus a fresh posting plus new-grad language
    # adds to well over 100 on its own), and a "score" that quietly isn't
    # actually bounded by its own stated scale is more confusing than useful.
    score = min(score, 100)

    job["score"] = round(score, 1)
    job["match_reasons"] = reasons
    return job


def rank_jobs(jobs: list[dict], profile: dict) -> list[dict]:
    seen = set()
    deduped = []
    for j in jobs:
        # Location is part of the key — many boards post the identical
        # title at several offices, and those are genuinely different
        # postings worth seeing separately.
        key = (_norm(j.get("company", "")), _norm(j.get("title", "")), _norm(j.get("location", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)

    kept = [j for j in deduped if not is_excluded(j, profile)]
    scored = [score_job(j, profile) for j in kept]
    scored.sort(key=lambda j: j["score"], reverse=True)
    return scored
