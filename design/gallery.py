#!/usr/bin/env python3
"""Rebuild design/gallery.html from whatever is on disk.

ponytail: scans the directory instead of keeping a manifest, so nothing can
drift out of sync with the files. Ceiling: rescans everything each run, which
is fine at 15 variants and would not be at 15,000.
"""
import html
import pathlib
import re

HERE = pathlib.Path(__file__).parent
ITER = HERE / "iterations"

TOTAL = re.compile(r"^TOTAL:\s*(\d+)", re.M)
TITLE = re.compile(r'^#\s*\S+\s*[—\-]?\s*(.+?)\s*(?:—\s*judge.*)?$', re.M)
MOVE = re.compile(r"^## The one change.*?\n+(.+?)(?:\n\n|\Z)", re.S | re.M)
# The judge's total, and it is deliberately anchored to the LABEL rather than to
# a position. Three rounds produced three card layouts: two put the total first
# among the bold numbers, and round 3 bolded every criterion, so "the first bold
# number" silently read the ask score as the total and named the wrong leader.
# Every layout so far writes the total on a row saying 'total' or '/70'.
# One regex cannot do it: the label itself contains a number ("Judge total (70)"),
# so find the row and take the LAST number on it.
LABEL = re.compile(r"total|judge\s*/\s*70", re.I)
NUM = re.compile(r"\d+(?:\.\d)?")
# The out-of marks, which are never the score: /25 /25 /20 /70.
DENOM = {"70", "25", "20"}


def judge_total(text):
    """The judge's 70-point total, from whichever card layout this round used.

    Three rounds produced three layouts, so this anchors on the LABEL and not on
    a position — 'first bold number' silently read round 3's ask score as the
    total and named the wrong leader. Two shapes exist: the label and the value
    on one row, and a header row whose values land on the next line.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not LABEL.search(line):
            continue
        # The label's own row, then the next two — a header row is followed by
        # markdown's |---|---| separator before the values arrive.
        for row in lines[i:i + 3]:
            if set(row.strip()) <= set("|- "):
                continue
            nums = [n for n in NUM.findall(row) if n not in DENOM]
            if nums:
                return float(nums[-1])
    return None
LANE = {"a": "atlas", "b": "depart", "c": "wildcard"}


def read(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def variants():
    for d in sorted(ITER.iterdir()):
        if not (d / "index.html").exists():
            continue
        score, judge = read(d / "SCORE.md"), read(d / "JUDGE.md")
        m, j = TOTAL.search(score), judge_total(judge)
        # A variant is named before it is judged, so NOTES is the last fallback
        # — otherwise a round in progress shows three blank cards.
        t = (TITLE.search(judge) or TITLE.search(score)
             or TITLE.search(read(d / "NOTES.md")))
        c = MOVE.search(score)
        rnd, _, lane = d.name.partition("-")
        yield {
            "id": d.name,
            "round": rnd,
            "lane": LANE.get(lane, lane),
            # The judge's 70 is the score every round actually has; the
            # evaluators' 30 exists for one variant only, so it is a footnote
            # rather than the headline.
            "judge": j,
            "name": (t.group(1).strip().strip('"“”') if t else ""),
            "total": int(m.group(1)) if m else None,
            "note": (c.group(1).strip() if c else "").split("\n")[0],
            "scored": bool(score),
            "judged": bool(judge),
        }


def card(v, best):
    n = html.escape(v["name"])
    note = html.escape(v["note"])
    j = v["judge"]
    badge = (f"{j:g}" if j is not None else "—")
    cls = "hi" if j is not None and j == best else ""
    links = [f'<a href="iterations/{v["id"]}/index.html"'
             f' target="_blank" rel="noopener">open</a>']
    if v["judged"]:
        links.append(f'<a href="iterations/{v["id"]}/JUDGE.md">verdict</a>')
    if v["scored"]:
        links.append(f'<a href="iterations/{v["id"]}/SCORE.md">craft</a>')
    if v["total"] is not None:
        note = note or f"evaluator half: {v['total']}/30"
    return f"""<article class="c {cls}">
  <a class="shot" href="iterations/{v['id']}/index.html" target="_blank" rel="noopener">
    <iframe src="iterations/{v['id']}/index.html" loading="lazy" title="{v['id']}"></iframe>
  </a>
  <div class="m">
    <span class="id">{v['id']} · {v['lane']}</span>
    <span class="sc">{badge}<small>/70</small></span>
  </div>
  <h2>{n or '&nbsp;'}</h2>
  <p>{note}</p>
  <p class="l">{' · '.join(links)}</p>
</article>"""


def main():
    vs = list(variants())
    judged = [v for v in vs if v["judge"] is not None]
    best = max((v["judge"] for v in judged), default=None)
    lead = next((v["id"] for v in judged if v["judge"] == best), "—")
    rounds = sorted({v["round"] for v in vs})
    blocks = []
    for r in rounds:
        mine = [v for v in vs if v["round"] == r]
        verdict = HERE / "rounds" / f"{r}-verdict.md"
        link = (f' · <a href="rounds/{r}-verdict.md">verdict</a>'
                if verdict.exists() else "")
        blocks.append(
            f'<h2 class="rh">{r} · {len(mine)} variants{link}</h2>\n'
            f'<div class="g">\n'
            + "\n".join(card(v, best) for v in mine)
            + "\n</div>")
    cards = "\n".join(blocks)
    top = f"{best:g}" if best is not None else "—"
    (HERE / "gallery.html").write_text(f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROLE·ATLAS — design harness gallery</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin:0; padding:2rem; font:15px/1.45 Inter,system-ui,sans-serif;
         background:#fff; color:#111; }}
  @media (prefers-color-scheme: dark) {{ body {{ background:#0d0d0d; color:#eee; }} }}
  h1 {{ font-size:1.1rem; letter-spacing:.12em; text-transform:uppercase;
       font-weight:700; margin:0 0 .3rem; }}
  .sub {{ color:#8a8a8a; font-size:12px; letter-spacing:.08em;
         text-transform:uppercase; margin:0 0 2rem; }}
  .g {{ display:grid; gap:1.6rem;
       grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); }}
  .c {{ border-top:2px solid currentColor; padding-top:.6rem; }}
  .c.hi {{ border-top-color:#E30613; }}
  .shot {{ display:block; height:250px; overflow:hidden; border:1px solid #d5d5d5;
          background:#fff; position:relative; }}
  .shot::after {{ content:""; position:absolute; inset:0; }}
  iframe {{ width:1280px; height:1000px; border:0;
           transform:scale(.36); transform-origin:0 0; pointer-events:none; }}
  .m {{ display:flex; justify-content:space-between; align-items:baseline;
       margin-top:.5rem; font-size:11px; letter-spacing:.11em;
       text-transform:uppercase; font-weight:600; }}
  .sc {{ font-size:20px; letter-spacing:0; font-variant-numeric:tabular-nums; }}
  .c.hi .sc {{ color:#E30613; }}
  h2 {{ font-size:15px; font-weight:600; margin:.25rem 0 .3rem; }}
  p {{ margin:0 0 .3rem; color:#4a4a4a; font-size:13px; }}
  @media (prefers-color-scheme: dark) {{ p {{ color:#aaa; }}
    .shot {{ border-color:#333; }} }}
  .l a {{ color:inherit; }}
  .rh {{ font-size:12px; letter-spacing:.11em; text-transform:uppercase;
        font-weight:700; margin:2.4rem 0 .9rem; padding-bottom:.4rem;
        border-bottom:1px solid currentColor; }}
  .rh:first-of-type {{ margin-top:0; }}
  .sc small {{ font-size:11px; opacity:.5; letter-spacing:.06em; }}
</style>
<h1>Design harness — every variant, kept</h1>
<p class="sub">{len(vs)} variants · {len(judged)} judged · leader {lead} at {top}/70</p>
<p>Scores are the judge's 70 subjective points — the ask, the feel of moving
through it, originality. Craft and translation are graded separately and exist
for one variant only. A clean, complete, faultless page scores 62.</p>
{cards}
""", encoding="utf-8")
    print(f"gallery.html · {len(vs)} variants, {len(judged)} judged, leader {lead}")


if __name__ == "__main__":
    main()
