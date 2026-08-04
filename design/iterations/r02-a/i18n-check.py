#!/usr/bin/env python3
"""Hold the eight editions to each other.

"No orphaned English" is not a thing you can achieve by reading carefully; it is
a thing you achieve by making the failure mechanical. This reads the LANGS table
out of index.html and asserts three properties that, together, are what the
brief's flow 3 actually asks for:

  1. every edition holds exactly the key set the English edition holds — a
     missing key falls back to English at runtime, which is an orphaned string
     with extra steps;
  2. no edition repeats a key, because the second literal silently wins and the
     first one is a translation nobody will ever see;
  3. every string interpolates the same {placeholders} as its English original,
     because a dropped {n} is a sentence that renders a count-shaped hole.

It also lists keys the page never asks for, which is how a table rots.

    python3 design/iterations/r02-a/i18n-check.py

Exits non-zero on any failure, so it can sit in front of a commit.
"""
import re
import sys
from pathlib import Path

PAGE = Path(__file__).with_name('index.html')
TABLE = re.compile(r"LANGS(?:\.(\w+)|\['([\w-]+)'\]) = \{(.*?)\n\};", re.S)
ENTRY = re.compile(r"^\s*'((?:[^'\\]|\\.)+)': '((?:[^'\\]|\\.)*)',\s*$", re.M)
KEYLINE = re.compile(r"^\s*'((?:[^'\\]|\\.)+)':", re.M)
PLACE = re.compile(r'\{(\w+)\}')


def agree(editions, base, base_places):
    """Every edition holds the English key set, once each, same placeholders."""
    faults = []
    for name, body in editions.items():
        keys = KEYLINE.findall(body)
        seen = set()
        for k in keys:
            if k in seen:
                faults.append(f'{name}: duplicate key {k!r}')
            seen.add(k)
        for k in sorted(base - seen):
            faults.append(f'{name}: missing key {k!r}')
        for k in sorted(seen - base):
            faults.append(f'{name}: key {k!r} exists in no other edition')
        for k, v in ENTRY.findall(body):
            want = base_places.get(k)
            got = set(PLACE.findall(v))
            if want is not None and want != got:
                faults.append(f'{name}: {k!r} interpolates {sorted(got)}, '
                              f'English interpolates {sorted(want)}')
        print(f'{name:<9} {len(keys):>4} keys')
    return faults


def unreached(source, base):
    # A key nothing asks for is a key that will drift. r01-a answered
    # reachability by pairing quotes across the whole file, and this page's
    # prose comments broke it: an apostrophe in "the reader's colour" desyncs
    # every quote after it, and the checker cried wolf about five live strings.
    # Comments are stripped first, and then a key is reached if the literal
    # `'key'` appears anywhere in the remaining code — half the keys on this
    # page arrive through an array of pairs, a lookup map or a built prefix, and
    # a checker that only understood direct t() calls would be useless here.
    code = source
    for _, _, body in TABLE.findall(source):
        code = code.replace(body, '')
    code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.S)
    code = re.sub(r'(?m)^\s*//.*$', ' ', code)
    code = re.sub(r'(?m)<!--.*?-->', ' ', code, flags=re.S)
    plural_bases = set(re.findall(r"pl\(\s*'([^']+)'", code))
    built = {m for m in re.findall(r"`([\w.]+)\$\{", code) if m}
    built |= {m for m in re.findall(r"t\(`([\w.]+)\$\{", code) if m}
    faults = []
    for k in sorted(base):
        if f"'{k}'" in code:
            continue
        head, _, tail = k.rpartition('.')
        if tail in ('one', 'other') and head in plural_bases:
            continue
        if any(k.startswith(prefix) for prefix in built):
            continue
        faults.append(f'unused: {k!r} is in the table and on no code path')
    return faults


def missing_from_table(source, base):
    """A key the code names but no edition holds renders as the empty string —
    the worst failure here, because a blank label looks like a design decision
    rather than a bug. Two of these shipped in this file: `ev.k.seen` and
    `ev.k.board` were eaten by a sed that ran to end-of-line over a table line
    holding three pairs, and every check passed, because they went missing from
    all eight editions at once and the eight therefore still agreed.

    So this does not look for `t('...')` calls. Half the keys on this page are
    handed to a helper (`fld('ev.k.seen', ...)`) or sit in an array of pairs.
    It looks at EVERY string literal in the code that is shaped like a key, and
    asks the table for it. Storage keys and dotted file names are the two other
    things on this page shaped that way, so they are named out explicitly.
    """
    code = source
    for _, _, body in TABLE.findall(source):
        code = code.replace(body, '')
    code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.S)
    code = re.sub(r'(?m)^\s*//.*$', ' ', code)
    code = re.sub(r'<!--.*?-->', ' ', code, flags=re.S)
    KEYISH = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-zA-Z0-9]+){1,3}$")
    NOT_A_KEY = re.compile(r"^(?:ra2|data|first|companies|build|index)\.|"
                           r"\.(?:json|html|js|py|com|dev|org)$")
    faults = []
    for lit in sorted(set(re.findall(r"'((?:[^'\\\n]|\\.)+)'", code))):
        if not KEYISH.match(lit) or NOT_A_KEY.search(lit):
            continue
        if lit in base:
            continue
        head, _, tail = lit.rpartition('.')
        if tail in ('one', 'other') and f'{head}.other' in base:
            continue
        faults.append(f'asked but absent: {lit!r} is named in the code and '
                      f'held by no edition')
    return faults


def main() -> int:
    source = PAGE.read_text(encoding='utf-8')
    editions = {(a or b): body for a, b, body in TABLE.findall(source)}
    if 'en' not in editions:
        print('no English edition found — has the table moved?')
        return 1

    base = set(KEYLINE.findall(editions['en']))
    base_places = {k: set(PLACE.findall(v)) for k, v in ENTRY.findall(editions['en'])}
    faults = (agree(editions, base, base_places) + unreached(source, base)
              + missing_from_table(source, base))

    if faults:
        print()
        for f in faults:
            print(f)
        print(f'\n{len(faults)} fault(s)')
        return 1
    print('\nall editions agree')
    return 0


if __name__ == '__main__':
    sys.exit(main())
