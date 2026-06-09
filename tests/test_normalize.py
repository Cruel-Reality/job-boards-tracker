"""Tests for source-agnostic field derivation helpers."""

import pytest

from app.normalize import infer_remote


@pytest.mark.parametrize(
    "location,expected",
    [
        ("Remote", True),
        ("Remote - US", True),
        ("remote (anywhere)", True),
        ("New York, NY", False),
        ("San Francisco, CA", False),
        (None, True),
        ("", True),
    ],
)
def test_infer_remote(location, expected):
    assert infer_remote(location) is expected
