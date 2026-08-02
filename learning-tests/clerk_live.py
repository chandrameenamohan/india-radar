#!/usr/bin/env python3
"""T11.1 — what Clerk actually is, before the site depends on it.

SPEC v3 bets that accounts can arrive without a backend: Clerk's browser SDK on
the static page, one publishable key, nothing of ours holding a credential. This
measures the bet against the real instance rather than the documentation.

Run: .venv/bin/python learning-tests/clerk_live.py   (four requests, ~2s)

Needs CLERK_PUBLISHABLE_KEY in .env — the publishable one, `pk_`. If this file
ever needs an `sk_` key to do its job, the design went wrong: a secret key in a
learning test is a secret key in the shell history of everyone who runs it.

WHAT WAS MEASURED (2026-08-02, instance regular-troll-50, development):

  1. `@clerk/clerk-js@latest` SERVES VERSION 4, NOT VERSION 5. The dist-tag
     resolves to 4.73.14; asking for `@5` resolves to 5.127.1. So the tag every
     quickstart reaches for is a major version behind the SDK the current docs
     describe, and a page written against v5 docs and loaded with `@latest`
     would fail on API that does not exist yet in the code it got. Pin the major.

  2. The frontend API host is DERIVABLE FROM THE KEY — it is base64 in the key's
     third segment, with a trailing `$`. Nothing needs to be configured
     separately, and nothing needs to be looked up in the dashboard. That is why
     the page needs exactly one string.

  3. `/v1/environment` ANSWERS WITH NO KEY AND NO PARAMS. The whole instance
     configuration — enabled strategies, password policy, session mode — is
     public to anyone holding the host, which anyone holding the page has. This
     is not a leak; it is the model. It is worth having measured, because it
     settles that the publishable key is public in fact and not just in name.

  4. THE INSTANCE ENABLES MORE THAN WAS ASKED FOR. Configured by hand: email and
     Google. Actually on: email, Google, GitHub, and **LinkedIn OIDC**. Clerk's
     defaults, not a mistake — but three of those put a "sign in with" button on
     the page, and the page should show what it means to offer. LinkedIn is the
     interesting one: TASKS.md F3 wants the reader's own LinkedIn identity and
     wants it supplied by the reader rather than scraped, and an OIDC sign-in is
     exactly that, volunteered. Not today's feature. Worth not turning off.

  5. `password: required`, `single_session_mode: true`. Email sign-up therefore
     costs the reader a password; there is no magic-link-only path unless the
     instance is reconfigured.

  6. THE ACCOUNT PORTAL LIVES ON A DIFFERENT HOST than the frontend API —
     `regular-troll-50.accounts.dev` versus `regular-troll-50.clerk.accounts.dev`
     — and `sign_in_url` points at it. So the redirect flow SENDS THE READER OFF
     THIS SITE to a Clerk-branded page and back. That decides an open question in
     T11.1's favour: mount Clerk's components on our own page instead. The reader
     signing in should never leave roleatlas.sennamind.com, and with `<SignIn />`
     mounted locally they do not have to.

  7. BOT PROTECTION MAKES AN AUTOMATED SIGN-UP IMPOSSIBLE HERE, both ways in.
     `signUp.create()` from the page returns `captcha_invalid` ("Error loading
     CAPTCHA"). Driving Clerk's real modal instead gets further and then stops
     harder: the sign-up form renders a Cloudflare Turnstile widget, its
     `cf-turnstile-response` field stays empty in the headless browser, and
     Continue stays disabled waiting for a token that never comes. So the
     authenticated half of T11.1 — sign up, reload, still signed in — cannot be
     gated from here at all. Two consequences worth having in writing:
       * Turning bot protection off for the DEVELOPMENT instance would unblock
         it. Production keeps it. That is a dashboard toggle, not code.
       * Any custom sign-up form this project ever builds (F2 and F3 both want
         onboarding of their own) inherits this: a headless flow needs a
         `#clerk-captcha` node for the widget, or it needs the prebuilt
         component. Discovering that during a redesign would be expensive.
     This is also the second time this project has been told the same thing by a
     different vendor: an automated client is not a browser, and the parts of the
     web that care will say so. `src/net.py` exists because of the first time.
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.net import get_bytes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def publishable_key() -> str:
    """The key from .env, or a clear failure. Never a secret key."""
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("CLERK_PUBLISHABLE_KEY="):
            key = line.split("=", 1)[1].strip()
            assert key.startswith("pk_"), f"not a publishable key: {key[:8]}"
            return key
    raise SystemExit("CLERK_PUBLISHABLE_KEY missing from .env")


def frontend_host(key: str) -> str:
    """Finding 2: the host is inside the key.

    `pk_test_<base64>` where the decoded text is the host with a trailing `$`.
    The padding is re-added because Clerk strips it.
    """
    encoded = key.split("_", 2)[2]
    return base64.b64decode(encoded + "==").decode().rstrip("$")


def main() -> None:
    key = publishable_key()
    host = frontend_host(key)
    print(f"key      {key[:12]}… ({len(key)} chars)")
    print(f"host     {host}")

    # Finding 1: what the dist-tags actually resolve to. curl follows redirects,
    # so the resolved version is read out of the URL curl ended up at rather than
    # from a Location header we would have to not-follow to see.
    print("\n--- dist tags ---")
    resolved = {}
    for tag in ("latest", "5"):
        url = f"https://{host}/npm/@clerk/clerk-js@{tag}/dist/clerk.browser.js"
        status, body = get_bytes(url, timeout=30)
        # The served file states its own version; trust the artifact, not the
        # URL. `version:"x.y.z"` is how the bundle records it — measured, not
        # guessed: the Location header would also say, but get_bytes follows
        # redirects by design and the header is gone by the time we see the body.
        found = re.search(rb'version:"(\d+\.\d+\.\d+)"', body)
        version = found.group(1).decode() if found else "?"
        resolved[tag] = version
        print(f"  @{tag:<7} {status}  {len(body):>9,} bytes  version {version}")

    assert resolved["5"].startswith("5."), f"@5 no longer serves v5: {resolved['5']}"
    if not resolved["latest"].startswith("5."):
        print(f"  ^ FINDING 1 HOLDS: @latest is {resolved['latest']}, a major behind @5.")

    # Finding 3: the environment is readable with nothing but the host.
    print("\n--- /v1/environment, no key, no params ---")
    status, body = get_bytes(f"https://{host}/v1/environment", timeout=30)
    assert status == 200, f"environment returned {status}"
    env = json.loads(body)

    auth = env["auth_config"]
    social = [k for k, v in env["user_settings"]["social"].items() if v.get("enabled")]
    display = env["display_config"]

    print(f"  strategies       {auth['identification_strategies']}")
    print(f"  social enabled   {social}")
    print(f"  password         {auth['password']}")
    print(f"  single session   {auth.get('single_session_mode')}")
    print(f"  instance type    {display.get('instance_environment_type')}")
    print(f"  sign_in_url      {display.get('sign_in_url')}")

    # Finding 4: email and Google were asked for; assert they are actually on,
    # and report the rest rather than assuming the dashboard matches intent.
    assert "email_address" in auth["identification_strategies"], "email sign-in is off"
    assert "oauth_google" in social, "Google sign-in is off"
    extra = set(social) - {"oauth_google"}
    if extra:
        print(f"  ^ FINDING 4: also enabled, unasked: {sorted(extra)}")

    # Finding 6: the portal is elsewhere, so a redirect flow leaves the site.
    portal = display.get("sign_in_url", "")
    if portal and host not in portal:
        print(f"  ^ FINDING 6 HOLDS: portal host is not the API host — {portal}")
        print("    Mount components locally; do not redirect the reader off-site.")

    print("\nAll assertions held.")


if __name__ == "__main__":
    main()
