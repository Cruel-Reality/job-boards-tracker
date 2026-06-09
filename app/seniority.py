"""Map a job title to a coarse seniority bucket.

Ordered keyword matcher like app.categorize: the first bucket whose keyword
appears in the lowercased title wins, so order encodes precedence (executive and
management levels before individual-contributor levels). Returns None when the
title carries no seniority signal (e.g. a plain "Software Engineer").

This is noisier than category: titles vary widely, and the word "manager" appears
in non-management roles (Product Manager, Program Manager), which land in the
manager bucket. Treat results as a best-effort hint, not ground truth.
"""

from app.orm_models import SeniorityEnum

# Ordered (bucket, keywords). First keyword hit, top to bottom, decides.
_SENIORITY_KEYWORDS: list[tuple[SeniorityEnum, tuple[str, ...]]] = [
    (SeniorityEnum.intern, ("intern", "co-op", "coop", "apprentice", "trainee")),
    # C-suite abbreviations are unsafe as substrings ("cto" is inside "director"),
    # so match on the spelled-out "chief"; titles almost always include it.
    (SeniorityEnum.executive, ("chief", "c-level")),
    (SeniorityEnum.director, ("director", "vp ", "vice president", "head of")),
    (SeniorityEnum.manager, ("manager", "supervisor")),
    (SeniorityEnum.lead, ("lead",)),
    (SeniorityEnum.staff, ("staff", "principal", "distinguished", "fellow")),
    (SeniorityEnum.senior, ("senior", "sr ", "sr.", "snr")),
    (SeniorityEnum.mid, ("mid-level", "midlevel", "intermediate", " ii", " iii")),
    (
        SeniorityEnum.entry,
        ("junior", "jr ", "jr.", "entry", "associate", "new grad", "graduate"),
    ),
]


def classify_seniority(title: str) -> SeniorityEnum | None:
    """Return the best-guess seniority bucket for a title, or None if unsignaled."""
    text = title.lower()
    for level, keywords in _SENIORITY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return level
    return None
