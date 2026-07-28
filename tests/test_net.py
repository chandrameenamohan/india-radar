"""The status/body split in net.get, exercised offline.

curl appends `%{http_code}` to the body on stdout, so get() slices the last three
characters back off. Get that wrong and every body ships with "200" glued to its
tail while every status reads as 0 — silently, since nothing else inspects it.
"""
import pytest

from src.net import fetch, get


@pytest.mark.network
def test_unreachable_url_is_status_zero():
    """Nothing listens on port 1, so curl never gets an answer and writes 000.
    A request that never happened must not look like a page."""
    assert get("http://127.0.0.1:1/nope", timeout=5) == (0, "")
    assert fetch("http://127.0.0.1:1/nope", timeout=5) is None
