"""The one way this project fetches a web page.

curl, not urllib: Cloudflare fingerprints the TLS handshake, and Python's is
tarpitted — the connection is accepted and then never answered, so even a socket
timeout doesn't fire and the run hangs instead of failing. curl's handshake gets
through. See learning-tests/FINDINGS.md.
"""
from __future__ import annotations

import subprocess

#: Load-bearing, not decoration: measured 403 with curl's default UA, 200 with
#: this one.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def fetch(url: str, timeout: int = 45) -> str | None:
    """GET a page, or None if it isn't a clean 200. A blocked page is a gap in
    the corpus, never fabricated data.

    Follows redirects: careers pages are routinely a bare domain redirecting to
    www, and treating that as unreachable would drop live companies.
    """
    done = subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--max-time", str(timeout), "-A", UA, url],
        capture_output=True,
    )
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", errors="replace")
