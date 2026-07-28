"""No test in this suite touches the network.

VERIFICATION.md is explicit that `make check` must not go red because somebody
else's site is down. That held by convention right up until slug resolution grew
a second network step *inside* `resolve_all` (T2.2's guessing pass), at which
point two T2.1 tests that stub `fetch` began silently probing live Greenhouse
boards — 20 seconds a run, and red whenever Greenhouse is.

So it is structural now: an unstubbed call fails the test that made it and names
the URL, rather than quietly buying a dependency on somebody's uptime.
"""
import pytest

import src.net


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    """Marked `network` opts out — reserved for the tests that ARE the fetching
    contract. The only one today dials 127.0.0.1:1, so it is local and cannot go
    red on somebody else's outage either.
    """
    if "network" in request.keywords:
        return

    def refuse(url: str, *args: object, **kwargs: object) -> None:
        raise AssertionError(f"unstubbed network call to {url} — stub it in the test")

    # get_bytes is the one door: net.get and net.fetch both go through it.
    monkeypatch.setattr(src.net, "get_bytes", refuse)
