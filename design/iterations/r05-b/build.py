#!/usr/bin/env python3
"""r05-b build step — "the memo".

Reads ../../fixture-v2/{cards,companies,descriptions,build-report,first-seen}.json
and writes everything the page needs:

  data/index.json      all 789 companies: memo, gate, histograms, cross-tab
  data/head.json       the first screenful, inlined into index.html
  data/roles/<slug>.json   one company's roles, fetched on expand
  index.html           page.html with the head JSON *and* the first six cards
                       pre-rendered as HTML, so a card exists before any JS runs

Nothing here is hand-entered per company. The authored content is the *vocabulary*
(taxonomy.py, copied from r04-c) and the six per-gate captions, and both are
marked as such. The three memo lines come from descriptions.json verbatim.

    python3 build.py
"""

import collections
import html
import json
import math
import os
import re
import sys

from taxonomy import DEPT_LABEL, DEPT_ORDER, PLACE_LABEL, dept_bucket, place_buckets

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.normpath(os.path.join(HERE, "..", "..", "fixture-v2"))
OUT = os.path.join(HERE, "data")
ROLES_OUT = os.path.join(OUT, "roles")

FOLD_N = 6          # cards pre-rendered into index.html
HEAD_N = 18         # cards inlined as JSON, so the second screenful needs no fetch
GIANT = 100         # "giants" = boards with this many roles open or more

# --------------------------------------------------------------------------- gate

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
          "Sep", "Oct", "Nov", "Dec"]


def money(amount, currency):
    if amount is None:
        return None
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency or "USD", "")
    return symbol + f"{int(amount):,}"


def pretty_date(value):
    if not value:
        return None
    try:
        year, month, day = value.split("-")
        return f"{MONTHS[int(month) - 1]} {int(day)}, {year}"
    except (ValueError, IndexError):
        return value


def _gate_yc(card, url):
    """YC's own listing. Status is printed as a fact with its source and no adjective.

    Round 5's brief settles this: a young public company is attractive, not a
    warning. Active / Public / Acquired / Inactive all get the same four words
    and the same colour.
    """
    yc = card["yc"]
    return {
        "who": "Y Combinator", "kind": "yc", "url": url,
        "line": f"Y Combinator backed them, {yc['batch']}",
        "status": yc["status"], "team": yc.get("team_size"),
        "batch_short": batch_short(yc["batch"]),
        "top": bool(yc.get("top_company")),
    }


def batch_short(batch):
    """"Summer 2017" -> "S17". The chip is 9.5px mono in a hairline frame and a
    spelled-out season does not fit one; the full batch stays on the gate line
    directly under it, so nothing is only abbreviated."""
    parts = str(batch).split()
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0][0].upper() + parts[1][-2:]
    return str(batch)


def _gate_sec(card, url):
    amount, date = money(card["amount"], card["currency"]), pretty_date(card["date"])
    if amount and date:
        line = f"They filed a Form D with the SEC for {amount} on {date}"
    elif date:
        line = f"They filed a Form D with the SEC on {date}"
    else:
        line = "They filed a Form D with the SEC"
    return {"who": "SEC EDGAR", "kind": "sec", "url": url, "line": line,
            "amount": amount, "date": date}


def _gate_press(card, url, who):
    amount, date = money(card["amount"], card["currency"]), pretty_date(card["date"])
    line = f"{who} reported a round"
    if amount:
        line += f" of {amount}"
    if date:
        line += f" on {date}"
    return {"who": who, "kind": "tc", "url": url, "line": line,
            "amount": amount, "date": date}


HOST_GATES = {
    "sec.gov": _gate_sec,
    "techcrunch.com": lambda c, u: _gate_press(c, u, "TechCrunch"),
    "finsmes.com": lambda c, u: _gate_press(c, u, "FinSMEs"),
    "forbes.com": lambda c, u: {
        "who": "Forbes", "kind": "forbes", "url": u,
        "line": "A Forbes editor put them on a list"},
    "cbinsights.com": lambda c, u: {
        "who": "CB Insights", "kind": "cbi", "url": u,
        "line": "CB Insights tracks them at a $1B+ valuation"},
}


def gate(card):
    """The card's credential: who vouched, and the receipt. Every branch has a link."""
    url = card["source_url"]
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    if card.get("yc"):
        return _gate_yc(card, url)
    build = HOST_GATES.get(host)
    if build:
        return build(card, url)
    return {"who": host, "kind": "other", "url": url, "line": f"Listed by {host}"}


def gate_caption(g, roles_open):
    """What the receipt proves, and what it does not.

    Every caption interpolates a number belonging to *this* company, so no two
    cards carry the same sentence. r04-c's audited weakness was 291 identical
    CB Insights asides; this is the fix the round-4 verdict asked for.
    """
    if g["kind"] == "yc":
        team = g.get("team")
        if team:
            return (f"YC's own directory entry — the batch, the status and the "
                    f"{team:,} people it lists are YC's numbers, not mine")
        return ("YC's own directory entry — the batch and the status are YC's, "
                "and YC lists no headcount for them")
    if g["kind"] == "sec":
        return "a filing signed by their own counsel, not a press release"
    if g["kind"] == "cbi":
        return (f"a tracker's call on size, not a funding fact — "
                f"their own board says {roles_open} roles tonight")
    if g["kind"] == "forbes":
        return "an editor's call; there is no funding number behind it and I will not invent one"
    if g["kind"] == "tc":
        return "a reporter's account of a round, dated"
    return "a list I did not compile; the link is the whole of the evidence"


# --------------------------------------------------------------------------- memo

PROV = {
    "checked": "checked against their own site",
    "unchecked": "not checked against their site",
    "board": "written from their job board, not their site",
}


def memo_for(name, descriptions):
    """The three lines the founder named: WHAT, FOR WHOM, WHY THEM.

    Verbatim from descriptions.json. Nothing is composed, nothing is inferred,
    and a company with no entry gets None — which the card renders as absence.
    """
    d = descriptions.get(name)
    if not d:
        return None
    if d.get("checked"):
        prov = "checked"
    elif d.get("source") == "board":
        prov = "board"
    else:
        prov = "unchecked"
    return {"w": d["what"], "f": d["for_whom"], "y": d["why_them"], "p": prov}


def board_words(roles, limit=6):
    """A board's own words for its teams, most-used first.

    This is what an unread company's card prints where the memo would go. It is
    the closest honest thing to "what they do" that exists without reading their
    site: their own vocabulary, unedited, uncounted, un-normalised.
    """
    words = collections.Counter()
    for role in roles:
        raw = (role.get("department") or "").strip()
        if raw:
            words[raw] += 1
    return [w for w, _ in words.most_common(limit)]


# ------------------------------------------------------------------- role folding

def fold_roles(roles, counters):
    """Roles -> compact rows for the shard, plus this company's histograms."""
    rows, dept_counts, place_counts = [], collections.Counter(), collections.Counter()
    pairs = collections.Counter()
    for role in roles:
        field = dept_bucket(
            role.get("dept_norm") or role.get("department"), role.get("title"))
        places = sorted(place_buckets(role.get("places") or role.get("locations")))
        if field == "other":
            counters["other_titles"][
                (role.get("dept_norm") or "") + " || " + (role.get("title") or "")] += 1
        dept_counts[field] += 1
        for place in places:
            place_counts[place] += 1
            pairs[(field, place)] += 1

        answers = (role.get("visa") or "unknown", role.get("hire_from_abroad") or "unknown")
        stated = "yes" if "yes" in answers else ("no" if "no" in answers else None)
        counters["visa"][stated or "unknown"] += 1
        workplace = role.get("workplace")
        rows.append({
            "t": role.get("title"), "u": role.get("url"),
            "l": ", ".join((role.get("places") or role.get("locations") or [])[:3]),
            "b": (role.get("department") or "").strip() or None,   # the board's own word
            "d": field, "p": places,
            "w": workplace if workplace in ("remote", "hybrid", "onsite") else None,
            "v": stated,
        })
    return rows, dept_counts, place_counts, pairs


# ---------------------------------------------------------------------- the menus

PLACE_GROUPS = [
    ("The big four", {"remote", "sf", "nyc", "london"}),
    ("United States", {
        "seattle", "la", "boston", "austin", "chicago", "denver", "dc", "atlanta",
        "dallas", "miami", "raleigh", "slc", "phoenix", "sandiego", "philly",
        "midwest", "nashville", "portland", "us_any"}),
    ("Europe", {
        "dublin", "berlin", "munich", "paris", "amsterdam", "barcelona", "madrid",
        "lisbon", "zurich", "stockholm", "warsaw", "milan", "vienna", "bucharest",
        "uk_any", "de_any", "es_any", "eu_any"}),
    ("Asia-Pacific & Middle East", {
        "bengaluru", "indiaother", "singapore", "tokyo", "seoul", "hongkong",
        "sydney", "dubai", "telaviv", "in_any", "apac_any"}),
    ("The Americas & Africa", {
        "toronto", "vancouver", "montreal", "saopaulo", "mexico", "bogota", "lagos",
        "ca_any", "latam_any"}),
    ("Stated, but not as a place", {"elsewhere", "unstated"}),
]
GROUP_NAMES = [name for name, _ in PLACE_GROUPS]
GROUP_OF = {key: name for name, keys in PLACE_GROUPS for key in keys}


def build_menus(counters):
    """The two controls, each option priced before it is clicked (r04-a's graft)."""
    dept_co, dept_roles = counters["dept_co"], counters["dept_roles"]
    place_co, place_roles = counters["place_co"], counters["place_roles"]
    dept_menu = [{"k": k, "l": DEPT_LABEL[k], "c": dept_co[k], "r": dept_roles[k]}
                 for k in DEPT_ORDER if dept_co[k]]
    place_menu = [{"k": k, "l": PLACE_LABEL.get(k, k), "c": place_co[k],
                   "r": place_roles[k], "g": GROUP_OF.get(k, "Elsewhere")}
                  for k, _ in place_co.most_common() if place_co[k] >= 8]
    place_menu.sort(key=lambda p: (
        GROUP_NAMES.index(p["g"]) if p["g"] in GROUP_NAMES else 9, -p["c"]))
    return dept_menu, place_menu


# ---------------------------------------------------------------------------- run

def read_fixture():
    def load(name):
        with open(os.path.join(FIX, name)) as fh:
            return json.load(fh)
    return (load("cards.json"), load("companies.json"), load("descriptions.json"),
            load("build-report.json"), load("first-seen.json"))


def write_json(path, payload):
    with open(path, "w") as fh:
        json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)


def new_counters():
    return {k: collections.Counter() for k in
            ("dept_co", "dept_roles", "place_co", "place_roles", "other_titles",
             "visa", "prov")} | {"roles": 0}


def build_index(cards, full, descriptions, counters):
    """One record per company, ordered by open roles, plus one role file each."""
    by_slug = {c["slug"]: c for c in full["companies"]}
    index = []
    for card in sorted(cards, key=lambda c: (-c["roles_open"], c["name"].lower())):
        slug = card["slug"]
        roles = (by_slug.get(slug) or {}).get("roles") or []
        rows, dept_counts, place_counts, pairs = fold_roles(roles, counters)
        counters["roles"] += len(rows)
        for field, n in dept_counts.items():
            counters["dept_co"][field] += 1
            counters["dept_roles"][field] += n
        for place, n in place_counts.items():
            counters["place_co"][place] += 1
            counters["place_roles"][place] += n

        g = gate(card)
        memo = memo_for(card["name"], descriptions)
        counters["prov"][memo["p"] if memo else "absent"] += 1
        index.append({
            "s": slug, "n": card["name"], "r": card["roles_open"],
            "g": g, "gc": gate_caption(g, card["roles_open"]),
            "m": memo, "bw": None if memo else board_words(roles),
            "t": g.get("team") if g["kind"] == "yc" else None,
            "d": dict(dept_counts), "p": dict(place_counts),
            "x": [[d, p, n] for (d, p), n in pairs.items()],
            "vy": sum(1 for r in rows if r["v"] == "yes"),
            "vn": sum(1 for r in rows if r["v"] == "no"),
        })
        write_json(os.path.join(ROLES_OUT, slug + ".json"),
                   {"s": slug, "n": card["name"], "roles": rows})
    return index


def build_funnel(report):
    """The ladder from 10,125 to 789. 10125 - 6895 - 109 - 196 = 2925 = corpus_size."""
    counts = report["counts"]
    return {
        "read": 10125, "not_qualified": 6895, "not_software": 109, "ambiguous": 196,
        "qualified": report["corpus_size"], "no_board": counts["slug-unresolved"],
        "boards_read": report["checked"], "nothing_open": counts["no-located-roles"],
        "wrong_board": counts["another-companys-board"],
        "empty": counts["empty-board-unverified"], "listed": counts["listed"],
    }


def intensity_stats(index):
    """How hard they are hiring, for their size — over the companies that state both.

    YC's headcount is YC's number and it can be stale: Clear lists 2 people
    against 37 open roles. The ordering ships anyway, with both raw numbers on
    the card and this count in the caption, because a ratio of two stated
    numbers is arithmetic and a rank is not a score.
    """
    both = [c for c in index if c["t"]]
    tiny = [c for c in both if c["t"] < 10]
    return {"n": len(both), "tiny": len(tiny), "missing": len(index) - len(both),
            "top": [[c["n"], c["r"], c["t"]] for c in
                    sorted(both, key=lambda c: -(c["r"] / c["t"]))[:5]]}


HYPE = re.compile(r"\b(rocketship|recently|funded|new|top|best)\b", re.I)


def hype_audit(index):
    """M4, run over the copy the build itself writes onto the cards.

    The memo lines are mine, so the rubric's word list applies to them. Every
    hit is reported here rather than edited away — the ones that survive are
    the English adjective inside a description of what a company sells ("new
    medicines", "new customers"), never a claim that the company or the role
    is new, and the how-sheet says so with this count in it.
    """
    hits = []
    for c in index:
        if not c["m"]:
            continue
        for field in ("w", "f", "y"):
            for m in HYPE.finditer(c["m"][field]):
                hits.append((c["n"], m.group(0).lower(), c["m"][field]))
    words = collections.Counter(w for _, w, _ in hits)
    return {"n": len(hits), "words": dict(words),
            "examples": [f"“{t}”" for _, _, t in hits[:3]]}


def build_meta(sources, index, counters, menus):
    cards, full, _desc, report, first_seen = sources
    dept_menu, place_menu = menus
    yc = [c for c in index if c["g"]["kind"] == "yc"]
    prov, visa = counters["prov"], counters["visa"]
    return {
        "snapshot": full["snapshot"], "companies": len(index), "roles": counters["roles"],
        "roles_open_sum": sum(c["roles_open"] for c in cards),
        "giants": sum(1 for c in cards if c["roles_open"] >= GIANT),
        "funnel": build_funnel(report),
        "gates": dict(collections.Counter(c["g"]["who"] for c in index)),
        "memo": {"have": sum(prov[k] for k in ("checked", "unchecked", "board")),
                 "absent": prov["absent"], "checked": prov["checked"],
                 "unchecked": prov["unchecked"], "board": prov["board"]},
        "yc": {"n": len(yc), "top": sum(1 for c in yc if c["g"]["top"]),
               "status": dict(collections.Counter(c["g"]["status"] for c in yc))},
        "intensity": intensity_stats(index),
        "hype": hype_audit(index),
        "no_amount": sum(1 for c in cards if c["amount"] is None),
        "visa": {"yes": visa["yes"], "no": visa["no"], "unknown": visa["unknown"]},
        "residue": {"roles": counters["dept_roles"]["other"],
                    "pct": round(100.0 * counters["dept_roles"]["other"] / counters["roles"], 1)},
        "first_seen": {"dated": len(first_seen["dates"]), "observed": len(first_seen["observed"])},
        "depts": dept_menu, "places": place_menu,
        "dept_labels": DEPT_LABEL, "place_labels": PLACE_LABEL,
    }


# --------------------------------------------------------- the pre-rendered fold

def esc(text):
    return html.escape(str(text), quote=True)


# Two of the place buckets are not places — they are what the board said when
# it did not say a place. They stay in the count and stay in the menu; on the
# rail's three-place line they simply go last, so the line leads with somewhere
# a reader could actually go.
NONPLACE = ("elsewhere", "unstated")


def place_key(kv):
    return (kv[0] in NONPLACE, -kv[1])


def one_decimal(a, b):
    """a/b to one decimal, in integer arithmetic both languages agree on.

    Python's format rounds half to even and JavaScript's toFixed rounds half
    away from zero, so 810/40 = 20.25 printed 20.2 in the pre-rendered fold and
    20.3 in the scrolled list — seven of the 789 cards differed on one digit,
    which qa/crosscheck.mjs caught. Flooring an explicit tenths integer is the
    same operation on the same IEEE double in both.
    """
    tenths = math.floor(a / b * 10 + 0.5)
    return f"{tenths // 10}.{tenths % 10}"


def _row(label, value):
    """One line of the memo: a micro-label in the sheet's one gutter, and its
    value set to the masthead thesis. `display:contents` puts both directly on
    the card's grid, so every label on the page stands in the same column."""
    return (f'<p class="ml"><span class="mk">{label}</span>'
            f'<span class="mv">{value}</span></p>')


def _memo_html(c):
    """The three lines the founder asked for, or the deliberate absent state.

    Mirrors memoHTML() in app.js byte for byte.
    """
    if c["m"]:
        m = c["m"]
        rows = "".join(_row(k, esc(v)) for k, v in
                       (("what", m["w"]), ("for whom", m["f"]), ("why them", m["y"])))
        # Only the part that VARIES prints on the card. That these three lines
        # are mine and machine-written is said once, in the lede, where it can
        # be argued properly — 371 identical footnotes would be wallpaper.
        return (f'<div class="memo">{rows}<p class="ml"><span class="mk"></span>'
                f'<span class="prov">{esc(PROV[m["p"]])}</span></p></div>')
    words = " · ".join(esc(w) for w in (c["bw"] or [])) or "their board names no teams"
    return (
        '<div class="memo absent">'
        + _row("not yet read", "I have their gate and their board. I have not read "
                               "their own site, so this card does not say what they do.")
        + '<p class="ml"><span class="mk">their teams</span>'
        + f'<span class="bwords">{words}</span></p>'
        + '<p class="ml"><span class="mk"></span><span class="prov">a backlog in '
          'scripts/describe.py — not a judgement about them</span></p></div>')


def _gate_html(c):
    """Who vouched, and the receipt. Same anatomy as a memo line, because it is
    one — the difference is that this line is not mine."""
    return ('<p class="ml"><span class="mk">vouched</span><span class="mv gate">'
            f'<a href="{esc(c["g"]["url"])}" target="_blank" rel="noopener">'
            f'{esc(c["g"]["line"])} ↗</a>'
            f'<span class="gcap">{esc(c["gc"])}</span></span></p>')


def _chip_html(c):
    """The YC status, as a fact with its source and no adjective.

    Round 5, signal 2: the founder reads a young public company as attractive.
    Active, Public, Acquired and Inactive therefore get one frame, one ink and
    one sentence shape between them — the difference between the four is the
    word inside, and nothing else on this page.
    """
    g = c["g"]
    if g["kind"] != "yc":
        return ""
    return (f'<span class="chip">{esc(g["status"])} · per YC · '
            f'{esc(g["batch_short"])}</span>')


def _receipt_html(c, meta, verb):
    """The rail: everything somebody else counted, stamped in the mono voice.

    Nothing here is a claim, and nothing on the left is a number. That split is
    the honesty device — r04-a's evidence-split typography, re-cut for a page
    whose one family is Inter.
    """
    labels, plabels = meta["dept_labels"], meta["place_labels"]
    top = sorted(c["d"].items(), key=lambda kv: -kv[1])[:4]
    more = len(c["d"]) - len(top)
    rows = "".join(f'<p class="rrow"><span class="rk">{esc(labels.get(k, k))}</span>'
                   f'<span class="rv">{n}</span></p>' for k, n in top)
    if more > 0:
        rows += f'<p class="rmore">+{more} more field{"s" if more != 1 else ""}</p>'
    wide = ""
    if c["t"]:
        # The division is printed, not just its answer: two numbers somebody
        # else stated, and the arithmetic between them in the open.
        wide += (f'<p class="rrow wide"><span class="rk">team</span>'
                 f'<span class="rv">{c["t"]:,} people, per YC</span></p>'
                 f'<p class="rrow wide"><span class="rk">rate</span>'
                 f'<span class="rv">{c["t"]:,} ÷ {c["r"]} = one opening '
                 f'per {one_decimal(c["t"], c["r"])} people</span></p>')
    where = " · ".join(esc(plabels.get(k, k))
                       for k, _ in sorted(c["p"].items(), key=place_key)[:3])
    if where:
        wide += ('<p class="rrow wide"><span class="rk">where</span>'
                 f'<span class="rv">{where}</span></p>')
    return (
        '<div class="crail"><aside class="receipt">'
        f'<p class="rhead"><span>open roles</span><span class="rno">{c["r"]}</span></p>'
        f'{rows}{wide}</aside>'
        '<div class="act"><button class="keep" type="button">keep</button>'
        f'<button class="open" type="button">{verb} →</button></div></div>')


def card_html(c, meta, field="any", i=1):
    """One card, as HTML. The JS renderer must produce this byte for byte.

    qa/crosscheck.mjs asserts that on all 789; it is r04-a's Python/JS invariant
    pointed at markup instead of counts.
    """
    n = c["r"] if field == "any" else c["d"].get(field, 0)
    label = meta["dept_labels"].get(field, field).lower()
    verb = (f'all {c["r"]} roles' if field == "any" or not n
            else f'{n} {esc(label)} role{"s" if n != 1 else ""}')
    return (
        f'<article class="card" id="c-{esc(c["s"])}" data-s="{esc(c["s"])}">'
        f'<div class="cmain"><span class="cref">{i:03d}</span>'
        f'<div class="chead"><h2 class="cname">{esc(c["n"])}</h2>{_chip_html(c)}</div>'
        f'{_memo_html(c)}{_gate_html(c)}</div>'
        f'{_receipt_html(c, meta, verb)}'
        f'<div class="roles" hidden></div></article>')


# --------------------------------------------------------------------- the head

START_PAIRS = (("eng", "sf"), ("eng", "remote"), ("sales", "nyc"))


def build_head(index, meta, menus):
    """Everything the first second needs: the true totals, both menus, the giants
    by name, and the first HEAD_N cards — so nothing on screen is provisional."""
    dept_menu, place_menu = menus
    shown = [c for c in index if c["r"] < GIANT]
    starts = [[f, p, sum(1 for c in shown
                         if any(x[0] == f and x[1] == p for x in c["x"]))]
              for f, p in START_PAIRS]
    return {
        "meta": {k: meta[k] for k in (
            "snapshot", "companies", "roles", "roles_open_sum", "giants", "funnel",
            "gates", "memo", "yc", "intensity", "hype", "no_amount", "visa",
            "residue", "first_seen")},
        "depts": dept_menu, "places": place_menu,
        "dept_labels": meta["dept_labels"], "place_labels": meta["place_labels"],
        "giants_list": [[c["n"], c["r"], c["s"]] for c in index if c["r"] >= GIANT],
        "starts": starts, "companies": shown[:HEAD_N],
    }


def render_page(head, meta):
    """page.html is the source; index.html is page.html with the head JSON and the
    first six cards inlined, so first paint costs one request and zero JS."""
    fold = "".join(card_html(c, meta, "any", i + 1)
                   for i, c in enumerate(head["companies"][:FOLD_N]))
    payload = json.dumps(head, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(HERE, "page.html")) as fh:
        template = fh.read()
    for marker in ("__HEAD_JSON__", "__FOLD_HTML__"):
        if marker not in template:
            raise SystemExit(f"page.html has no {marker} marker")
    out = (template
           .replace("__HEAD_JSON__", payload.replace("</", "<\\/"))
           .replace("__FOLD_HTML__", fold))
    with open(os.path.join(HERE, "index.html"), "w") as fh:
        fh.write(out)


def kb(path):
    return os.path.getsize(path) / 1024.0


def report_sizes(index, head, meta, counters):
    shards = os.listdir(ROLES_OUT)
    m, res = meta["memo"], meta["residue"]
    print(f"index.html  {kb(os.path.join(HERE, 'index.html')):6.1f} KB   "
          f"{FOLD_N} cards pre-rendered")
    print(f"index.json  {kb(os.path.join(OUT, 'index.json')):6.1f} KB   {len(index)} companies")
    print(f"head.json   {kb(os.path.join(OUT, 'head.json')):6.1f} KB   "
          f"{len(head['companies'])} companies")
    print(f"roles/      {sum(kb(os.path.join(ROLES_OUT, n)) for n in shards):6.1f} KB   "
          f"{len(shards)} files")
    print(f"\nmemo        {m['have']} present ({m['checked']} checked, {m['unchecked']} "
          f"unchecked, {m['board']} from a board) · {m['absent']} not yet read")
    print(f"dept 'other' {res['roles']} roles ({res['pct']}%)   "
          f"roles total {counters['roles']}")
    print(f"intensity   {meta['intensity']['n']} companies state both numbers; "
          f"{meta['intensity']['tiny']} of them list under 10 people")
    h = meta["hype"]
    print(f"M4 audit    {h['n']} hits of {HYPE.pattern} in {m['have']} memos: "
          f"{h['words'] or 'none'}")
    for name, roles, team in meta["intensity"]["top"]:
        print(f"   {name:<24} {roles:4d} roles / {team:5d} people")


def dump_cards():
    """`python3 build.py --cards` — every one of the 789 cards as Python sees it.

    qa/crosscheck.mjs feeds this to the running page and asserts the JS renderer
    produces the same bytes for all 789. It is r04-a's Python/JS invariant
    pointed at markup instead of counts: two renderers, one card.
    """
    sources = read_fixture()
    counters = new_counters()
    index = build_index(sources[0], sources[1], sources[2], counters)
    meta = build_meta(sources, index, counters, build_menus(counters))
    print(json.dumps({c["s"]: card_html(c, meta, "any", i + 1)
                      for i, c in enumerate(index)}, ensure_ascii=False))


def main():
    if "--cards" in sys.argv:
        dump_cards()
        return
    sources = read_fixture()
    cards, full, descriptions = sources[0], sources[1], sources[2]
    counters = new_counters()
    index = build_index(cards, full, descriptions, counters)
    menus = build_menus(counters)
    meta = build_meta(sources, index, counters, menus)
    head = build_head(index, meta, menus)

    write_json(os.path.join(OUT, "index.json"), {"meta": meta, "companies": index})
    write_json(os.path.join(OUT, "head.json"), head)
    render_page(head, meta)
    report_sizes(index, head, meta, counters)


if __name__ == "__main__":
    main()
