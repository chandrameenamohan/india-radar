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


def get_bytes(url: str, timeout: int = 45, ua: str = UA) -> tuple[int, bytes]:
    """GET a URL, returning (status, body) with the body undecoded.

    Bytes, because not every source is a web page: SEC ships Form D as a zip
    archive, and decoding that as text corrupts it.

    `ua` is overridable because one host's requirement is another host's block —
    SEC serves 403 to the browser UA above and 200 to a declared contact string.
    """
    done = subprocess.run(
        [
            "curl", "--location", "--silent", "--max-time", str(timeout),
            "-A", ua, "--write-out", "%{http_code}", url,
        ],
        capture_output=True,
    )
    # curl appends the status to the body on stdout, and prints 000 when the
    # transfer never happened.
    body, status = done.stdout[:-3], done.stdout[-3:].decode("ascii", errors="replace")
    return (int(status) if status.isdigit() else 0), body


def get(url: str, timeout: int = 45) -> tuple[int, str]:
    """GET a URL, returning (status, body). Status 0 means the request never got
    an answer at all — DNS failure, refused connection, timeout.

    Follows redirects: careers pages are routinely a bare domain redirecting to
    www, and treating that as unreachable would drop live companies. The status
    reported is the final one.

    Callers that must tell a 404 from a 502 need this — a 404 board slug is a
    wrong slug, a 502 is a board we failed to read, and they send a company to
    different outcomes.
    """
    status, body = get_bytes(url, timeout)
    return status, body.decode("utf-8", errors="replace")


def fetch(url: str, timeout: int = 45) -> str | None:
    """GET a page, or None if it isn't a clean 200. A blocked page is a gap in
    the corpus, never fabricated data.
    """
    status, body = get(url, timeout)
    return body if status == 200 else None
