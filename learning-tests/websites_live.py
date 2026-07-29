"""T1.6 — where a company website can honestly be found, measured live.

Run: .venv/bin/python learning-tests/websites_live.py

Two questions, because the whole task rests on them:
  1. Which sources STATE a website, and for how many companies?
  2. For the ones that don't, does the article/profile page they link carry one
     that can be identified structurally rather than guessed?
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import cbinsights, forbes, techcrunch, yc
from src.finsmes import BASE
from src.finsmes import parse as parse_finsmes
from src.net import fetch
from src.slugs import key

_ANCHOR = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def host(url: str) -> str:
    return url.split("/")[2].removeprefix("www.").casefold()


def candidates(html: str, name: str, publisher: str) -> tuple[set[str], set[str]]:
    """(hosts linked under the company's own name, hosts linked as themselves)."""
    by_name: set[str] = set()
    by_self: set[str] = set()
    for match in _ANCHOR.finditer(html):
        url, text = match.group(1), _TAGS.sub("", match.group(2)).strip()
        if publisher in host(url):
            continue
        if key(text) and key(text) == key(name):
            by_name.add(host(url))
        elif key(text) == key(host(url)):
            by_self.add(host(url))
    return by_name, by_self


def sample(label: str, pairs: list[tuple[str, str]], publisher: str) -> None:
    print(f"\n== {label}: {len(pairs)} pages")
    with ThreadPoolExecutor(max_workers=8) as pool:
        pages = list(pool.map(lambda p: fetch(p[1], timeout=45), pairs))
    hit = 0
    for (name, _), page in zip(pairs, pages, strict=True):
        if page is None:
            print(f"  {name:28} UNREACHABLE")
            continue
        by_name, by_self = candidates(page, name, publisher)
        chosen = by_name or by_self
        verdict = next(iter(chosen)) if len(chosen) == 1 else f"AMBIGUOUS {sorted(chosen)}"
        hit += len(chosen) == 1
        print(f"  {name:28} name={sorted(by_name)} self={sorted(by_self)} -> {verdict}")
    print(f"  resolved {hit}/{len(pairs)}")


def main() -> None:
    directory = json.loads(fetch(yc.API, timeout=120) or "[]")
    stated = sum(1 for c in directory if c.get("website"))
    print(f"YC: {stated}/{len(directory)} state a website")

    rows = [row for payload in forbes.download() for row in forbes._rows(payload)]
    print(f"Forbes: {sum(1 for r in rows if r.get('webSite'))}/{len(rows)} state a website")

    page = fetch(f"{BASE}/category/usa")
    finsmes = parse_finsmes(page or "").records
    sample("FinSMEs articles", [(r["name"], r["source_url"]) for r in finsmes], "finsmes.com")

    url = (
        f"{techcrunch.API}?categories={techcrunch.CATEGORY}"
        "&per_page=100&page=1&_fields=title,link,date"
    )
    tc = techcrunch.parse(fetch(url, timeout=60) or "[]")
    sample(
        "TechCrunch articles",
        [(r["name"], r["source_url"]) for r in tc[:10]],
        "techcrunch.com",
    )

    unicorns = cbinsights.parse(fetch(cbinsights.UNICORNS, timeout=60) or "")
    sample(
        "CB Insights profiles",
        [(r["name"], r["source_url"]) for r in unicorns[:12]],
        "cbinsights.com",
    )


if __name__ == "__main__":
    main()
