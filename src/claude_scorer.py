"""Optional second-pass scorer: sends the top keyword-ranked postings to
the Claude API for genuine semantic judgment against your resume, instead
of just keyword overlap. Entirely optional — the pipeline works fine
without it, just with keyword scoring alone (see src/scorer.py).

Requires:
  - ANTHROPIC_API_KEY set (repo secret in CI, env var locally)
  - a "resume_text" key in your PROFILE_OVERRIDE_JSON with your actual
    resume text pasted in (see README)

Uses Haiku by default to keep cost low at this volume — override with
the CLAUDE_SCORE_MODEL env var if you want a stronger model.
"""
import json
import os
import re

MODEL = os.environ.get("CLAUDE_SCORE_MODEL", "claude-haiku-4-5")
BATCH_SIZE = 12

SYSTEM_PROMPT = (
    "You are scoring job postings against a candidate's resume for fit. "
    "For each posting, give a score from 0-100 (100 = excellent fit) and a "
    "one-sentence reason. Respond with ONLY a JSON array, no other text, no "
    'markdown code fences. Each element: {"id": <int>, "score": <int 0-100>, '
    '"reason": "<one sentence>"}.'
)


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def score_with_claude(jobs: list[dict], resume_text: str) -> list[dict]:
    """Mutates jobs in place, adding 'claude_score'/'claude_reason' where
    scoring succeeded. Order of the input list is preserved either way —
    call sort_by_claude_score() afterward if you want them reordered."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  [claude-scorer] ANTHROPIC_API_KEY not set — skipping, keyword score stands alone")
        return jobs
    if not resume_text:
        print("  [claude-scorer] no resume_text in profile override — skipping")
        return jobs

    try:
        import anthropic
    except ImportError:
        print("  [claude-scorer] 'anthropic' package not installed — skipping")
        return jobs

    client = anthropic.Anthropic(api_key=api_key)

    for batch_start in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[batch_start:batch_start + BATCH_SIZE]
        listing = "\n\n".join(
            f"[{i}] {j.get('title', '')} at {j.get('company', '')} ({j.get('location', '')})\n"
            f"{(j.get('description') or '')[:600]}"
            for i, j in enumerate(batch)
        )
        prompt = f"RESUME:\n{resume_text}\n\nPOSTINGS:\n{listing}"

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError) as e:
            # bad key / bad model id — won't fix itself on the next batch, stop burning calls
            print(f"  [claude-scorer] fatal config error, aborting: {e}")
            break
        except anthropic.RateLimitError as e:
            print(f"  [claude-scorer] batch at index {batch_start} rate-limited, skipping: {e}")
            continue
        except anthropic.APIStatusError as e:
            print(f"  [claude-scorer] batch at index {batch_start} server error {e.status_code}, skipping: {e}")
            continue
        except anthropic.APIConnectionError as e:
            print(f"  [claude-scorer] batch at index {batch_start} connection error, skipping: {e}")
            continue

        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            results = _extract_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"  [claude-scorer] batch at index {batch_start} returned unparseable JSON, skipping: {e}")
            continue

        if not isinstance(results, list):
            print(f"  [claude-scorer] batch at index {batch_start} returned non-list JSON, skipping")
            continue

        for r in results:
            idx = r.get("id")
            if idx is None:
                continue
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(batch):
                batch[idx]["claude_score"] = r.get("score")
                batch[idx]["claude_reason"] = r.get("reason")

    scored_count = sum(1 for j in jobs if j.get("claude_score") is not None)
    print(f"  [claude-scorer] scored {scored_count}/{len(jobs)} postings")
    return jobs


def sort_by_claude_score(jobs: list[dict]) -> list[dict]:
    """Re-sorts a list where some jobs have claude_score and some don't —
    falls back to the keyword score for any that failed to get scored."""
    return sorted(jobs, key=lambda j: j.get("claude_score") if j.get("claude_score") is not None else j["score"], reverse=True)
