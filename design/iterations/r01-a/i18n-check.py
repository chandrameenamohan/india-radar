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

    python3 design/iterations/r01-a/i18n-check.py

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
    # A key nothing asks for is a key that will drift. Reachability is answered
    # by looking for the literal anywhere in the code OUTSIDE the tables, rather
    # than by pattern-matching `t(...)` calls: half the keys on this page are
    # reached through a lookup map, a ternary, an option array or a `dept.` +
    # variable template, and a checker that only understood direct calls spent
    # its whole output crying wolf about forty live strings. `pl()` bases are
    # expanded to the two plural forms it can ask for.
    code = source
    for _, _, body in TABLE.findall(source):
        code = code.replace(body, '')
    literal = set(re.findall(r"'((?:[^'\\\n]|\\.)+)'", code))
    plural_bases = set(re.findall(r"pl\(\s*'([^']+)'", source))
    reached = set(literal)
    for b in plural_bases:
        reached |= {f'{b}.one', f'{b}.other'}
    # `t('dept.' + name)` and its kin: a key whose prefix is built and whose
    # tail is a value from the data or from a constant table.
    built = {m for m in re.findall(r"`([\w.]+)\$\{", source) if m}
    faults = []
    for k in sorted(base):
        if k in reached:
            continue
        # A counted noun is asked for by its base — sometimes as a literal in
        # the call, sometimes through a variable the call was handed.
        head, _, tail = k.rpartition('.')
        if tail in ('one', 'other') and head in reached:
            continue
        if any(k.startswith(prefix) for prefix in built):
            continue
        faults.append(f'unused: {k!r} is in the table and on no code path')
    return faults


def main() -> int:
    source = PAGE.read_text(encoding='utf-8')
    editions = {(a or b): body for a, b, body in TABLE.findall(source)}
    if 'en' not in editions:
        print('no English edition found — has the table moved?')
        return 1

    base = set(KEYLINE.findall(editions['en']))
    base_places = {k: set(PLACE.findall(v)) for k, v in ENTRY.findall(editions['en'])}
    faults = agree(editions, base, base_places) + unreached(source, base)

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
