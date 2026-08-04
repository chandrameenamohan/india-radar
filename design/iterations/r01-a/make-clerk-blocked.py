#!/usr/bin/env python3
"""Regenerate clerk-blocked.html from index.html.

The brief's one hard invariant is that the register renders when Clerk is
blocked, slow or broken, and the only way to hold a page to that is to open it
in that state. This writes a copy of index.html whose Clerk tag points at a
host that does not resolve — which is what a script blocker, an offline
machine, a corporate proxy and a provider outage all look like from inside the
page: the tag is present, the script never arrives, `window.Clerk` is undefined
when `load` fires.

Generated rather than hand-maintained so it cannot drift from the page it is
supposed to be testing.

    python3 design/iterations/r01-a/make-clerk-blocked.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
LIVE = 'src="https://regular-troll-50.clerk.accounts.dev/npm/@clerk/clerk-js@5/dist/clerk.browser.js"'
DEAD = 'src="https://blocked.invalid/clerk-js-that-never-arrives.js"'
BANNER = '''<!-- ================================================================
     GENERATED FIXTURE — do not edit. Rebuild with:
       python3 design/iterations/r01-a/make-clerk-blocked.py

     index.html with the Clerk tag pointed at a host that does not
     resolve. It exists so the brief's one hard invariant — "the register
     must still render when Clerk is blocked, slow, or broken" — can be
     driven in a browser rather than argued for in a comment. Open it and
     the register prints in full, the account control never appears, no
     reply card is shown, and the bookplate says the binding office did
     not answer.
     ================================================================ -->
'''


def main() -> int:
    source = (HERE / 'index.html').read_text(encoding='utf-8')
    if LIVE not in source:
        print('the Clerk script tag moved; this fixture needs updating')
        return 1
    out = source.replace(LIVE, DEAD)
    out = out.replace('<!doctype html>', '<!doctype html>\n' + BANNER, 1)
    (HERE / 'clerk-blocked.html').write_text(out, encoding='utf-8')
    print('wrote clerk-blocked.html')
    return 0


if __name__ == '__main__':
    sys.exit(main())
