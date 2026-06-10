"""Map a job title to a coarse seniority bucket.

Ordered keyword matcher like app.categorize, but matching on whole words (regex
word boundaries) rather than raw substrings, so "intern" does not fire on
"internal" and "vp" does not fire on "mvp". The first bucket whose keyword
appears in the lowercased title wins, so order encodes precedence (executive and
management levels before individual-contributor levels). Returns None when the
title carries no seniority signal (e.g. a plain "Software Engineer").

This is noisier than category: titles vary widely, and the word "manager" appears
in non-management roles (Product Manager, Program Manager), which land in the
manager bucket. Treat results as a best-effort hint, not ground truth.
"""

import re

from app.orm_models import SeniorityEnum

# Ordered (bucket, keywords). First keyword hit, top to bottom, decides. Keywords
# are matched as whole words, so no trailing-space/abbreviation tricks are needed.
_SENIORITY_KEYWORDS: list[tuple[SeniorityEnum, tuple[str, ...]]] = [
    (
        SeniorityEnum.intern,
        ("intern", "internship", "co-op", "coop", "apprentice", "trainee"),
    ),
    # C-suite abbreviations are noisy, so match on the spelled-out "chief"; titles
    # almost always include it.
    (SeniorityEnum.executive, ("chief", "c-level")),
    (SeniorityEnum.director, ("director", "vp", "vice president", "head of")),
    (SeniorityEnum.manager, ("manager", "supervisor")),
    (SeniorityEnum.lead, ("lead", "leader")),
    (SeniorityEnum.staff, ("staff", "principal", "distinguished", "fellow")),
    (SeniorityEnum.senior, ("senior", "sr", "snr")),
    (SeniorityEnum.mid, ("mid-level", "midlevel", "intermediate", "ii", "iii")),
    (
        SeniorityEnum.entry,
        ("junior", "jr", "entry", "associate", "new grad", "graduate"),
    ),
]


def classify_seniority(title: str) -> SeniorityEnum | None:
    """Return the best-guess seniority bucket for a title, or None if unsignaled."""
    text = title.lower()
    for level, keywords in _SENIORITY_KEYWORDS:
        if any(re.search(rf"\b{re.escape(kw)}\b", text) for kw in keywords):
            return level
    return None
