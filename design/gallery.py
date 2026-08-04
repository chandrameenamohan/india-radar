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
TITLE = re.compile(r"^#\s*\S+\s*[—-]\s*(.+)$", re.M)
MOVE = re.compile(r"^## The one change.*?\n+(.+?)(?:\n\n|\Z)", re.S | re.M)


def read(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def variants():
    for d in sorted(ITER.iterdir()):
        if not (d / "index.html").exists():
            continue
        score = read(d / "SCORE.md")
        m = TOTAL.search(score)
        t = TITLE.search(score)
        c = MOVE.search(score)
        yield {
            "id": d.name,
            "name": t.group(1).strip() if t else "",
            "total": int(m.group(1)) if m else None,
            "note": (c.group(1).strip() if c else "").split("\n")[0],
            "scored": bool(score),
        }


def card(v):
    n = html.escape(v["name"])
    note = html.escape(v["note"])
    total = v["total"]
    badge = f"{total}" if total is not None else "—"
    cls = "hi" if total is not None and total >= 80 else ""
    scored = (f'· <a href="iterations/{v["id"]}/SCORE.md">score</a>'
              if v["scored"] else "")
    return f"""<article class="c {cls}">
  <a class="shot" href="iterations/{v['id']}/index.html" target="_blank" rel="noopener">
    <iframe src="iterations/{v['id']}/index.html" loading="lazy" title="{v['id']}"></iframe>
  </a>
  <div class="m">
    <span class="id">{v['id']}</span>
    <span class="sc">{badge}</span>
  </div>
  <h2>{n or '&nbsp;'}</h2>
  <p>{note}</p>
  <p class="l">
    <a href="iterations/{v['id']}/index.html" target="_blank" rel="noopener">open</a>
    {scored}
  </p>
</article>"""


def main():
    vs = list(variants())
    ranked = sorted((v for v in vs if v["total"] is not None),
                    key=lambda v: -v["total"])
    lead = ranked[0]["id"] if ranked else "—"
    cards = "\n".join(card(v) for v in vs)
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
</style>
<h1>Design harness — every variant, kept</h1>
<p class="sub">{len(vs)} variants · {len(ranked)} scored · leader {lead}</p>
<div class="g">
{cards}
</div>
""", encoding="utf-8")
    print(f"gallery.html · {len(vs)} variants, {len(ranked)} scored")


if __name__ == "__main__":
    main()
