"""T11.1 — the account control, and the secret that must never ship with it.

Clerk issues two keys. The publishable one (`pk_`) is public by design and belongs
in the page — `learning-tests/clerk_live.py` finding 3 reads the whole instance
configuration out of Clerk with no key at all, so nothing is given away by it. The
secret one (`sk_`) grants admin over every account that will ever exist here:
impersonation, security settings, org admins.

The distinction is one character, in two strings that look alike at a glance,
copied from adjacent boxes on the same dashboard page. That is the entire reason
this file exists — and why it reads git history as well as the working tree. A key
committed and deleted in the next commit is a key that shipped; the fix is to
rotate it at Clerk, not to `git rm` it, and the only way anyone learns they must
is a check that keeps looking after the file is clean.
"""
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"

#: A Clerk secret key is the prefix AND a long body, and both halves of that are
#: load-bearing — each was measured by getting it wrong first.
#:
#: The prefix alone (a bare `sk_`) matches `task_` and `risk_`, so the history
#: check failed on this project's own task numbers. And the prefix with a
#: qualifier but no body matches PROSE ABOUT KEYS: the comment above this line
#: names the two forms, and the first thing the check found was itself.
#:
#: So: at least twenty key-ish characters after the qualifier. A mention of a key
#: is not a key; a key has a body. A check that cries wolf on every commit that
#: documents it is a check somebody eventually deletes, which is worse than not
#: having written it.
SECRET_RE = "sk_" + r"(test|live)_[A-Za-z0-9]{20,}"


def test_page_carries_a_publishable_key():
    """The control cannot mount without one, and a page that silently lost it
    would look identical until a reader tried to sign in."""
    html = PAGE.read_text()

    keys = re.findall(r'data-clerk-publishable-key="([^"]+)"', html)

    assert len(keys) == 1, f"expected exactly one publishable key, found {len(keys)}"
    assert keys[0].startswith("pk_"), f"not a publishable key: {keys[0][:8]}"


def test_page_holds_no_secret_key():
    """Invariant. The secret key must never reach the browser."""
    assert not re.search(SECRET_RE, PAGE.read_text()), (
        "a secret key is in the page. Rotate it at Clerk immediately — "
        "deleting the line is not enough, it has been served."
    )


def test_no_secret_key_in_any_reachable_commit():
    """The same invariant, over history rather than the working tree.

    `git log -p` over the whole of main, because the failure this guards is a key
    pasted, committed, noticed, and removed — after which every check that reads
    only the current tree goes green over a live credential.

    Skipped rather than failed outside a git checkout: a tarball of this project
    has no history to read, and a check that cannot run is not a check that found
    something.
    """
    done = subprocess.run(
        ["git", "log", "-p", "--all", "-G", SECRET_RE, "--format=%H %s"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if done.returncode != 0:
        pytest.skip("not a git checkout, or git unavailable")

    assert not done.stdout.strip(), (
        f"a secret key appears in git history:\n{done.stdout[:400]}\n"
        "Rotate the key at Clerk. Removing it from the tree does not unshare it."
    )


def test_clerk_sdk_is_pinned_to_a_major_version():
    """learning-tests/clerk_live.py finding 1: `@latest` serves 4.73.14, a major
    version behind the v5 API this page is written against. The tag is the trap;
    the pin is the fix, and this is what stops a future edit from undoing it."""
    html = PAGE.read_text()

    src = re.search(r'src="(https://[^"]*clerk-js@[^"]+)"', html)

    assert src, "the Clerk SDK script tag is gone"
    assert "@latest" not in src.group(1), "pinned to @latest, which serves v4"
    assert re.search(r"clerk-js@\d", src.group(1)), "SDK version is not pinned"


def test_account_control_gates_nothing():
    """SPEC v3's central promise, held by a test rather than by intent.

    The account markup is one empty div in the header. If a future edit ever makes
    the register conditional on a reader being signed in, the words that do it —
    Clerk.user guarding a render, a hidden class on a row — will appear inside the
    renderer, and this is the check standing there.
    """
    html = PAGE.read_text()
    opened = html.index("<script>")
    renderer = html[opened:html.index("</script>", opened)]

    assert "Clerk" not in renderer, (
        "the renderer references Clerk. The register is public: what it shows "
        "must not depend on who is reading it."
    )
