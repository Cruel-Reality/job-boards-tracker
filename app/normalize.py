"""Source-agnostic helpers for deriving normalized job fields.

Shared across job board sources so every source infers fields the same way (see
also app.categorize for the title-to-category mapping).
"""


def infer_remote(location: str | None) -> bool:
    """Best-guess remote flag from a location string.

    A "remote" mention counts as remote, and a posting with no location is assumed
    remote (nothing tying it to a physical office).
    """
    if not location:
        return True
    return "remote" in location.lower()
