# Learning-test findings — 2026-07-28

Five tests against the real dependencies, before any spec. Everything below is
measured, not assumed. Numbers are from actual runs; re-run the scripts to refresh.

## Verdict in one line

The ATS-first architecture is **confirmed viable and cheap**. MCA enrichment is
**viable but has two unresolved unknowns**. Three of my own beliefs were wrong,
and one of my tests was itself buggy in a way that would have shipped bad data.

---

## 1. ATS job boards — the primary pipeline

| Provider | Slugs OK | Latency | Notes |
|---|---|---|---|
| Greenhouse | 5/5 | **0.35s** median | `meta.total` matches returned count exactly — no pagination needed |
| Ashby | 5/5 | **~151s** flat | Works, but see below |
| Lever | 2/5 | ~1.1s | 3 slugs 404'd; the 2 that returned 200 returned **zero** postings |

**Greenhouse is the good citizen.** `boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false`,
unauthenticated, sub-second, complete in one call. Build around it.

**Ashby has a fixed ~151s latency that is independent of payload size** (114 jobs
and 750 jobs both took ~151s) **and independent of concurrency** (1, 4 and 12
concurrent callers all finished in ~151s wall). So it parallelises cleanly:
effective cost fell from 151s → 37.7s → **16.8s per company** as concurrency went
1 → 4 → 12. At concurrency 12 that's ~4.7h per 1000 Ashby companies.

Two cautions on Ashby:
- Latency **grew across runs**: ~50s in run 1, ~151s in runs 2 and 3. That reads
  as progressive throttling of a repeat caller. Needs backoff + caching, and the
  refresh job should not hammer it.
- At concurrency 12, **3 of 12 requests failed**. Budget for retries.

**Lever is a trap.** A wrong slug can return HTTP 200 with an empty array, which
is indistinguishable from "this company has no open roles". That silently zeroes
out rows. Any Lever result of zero must be treated as unverified, not as zero.

## 2. India detection — my test had a precision bug that would have shipped

I wrote a "better" India-matching rule using a case-**insensitive** regex for the
ISO prefix `IN-`. It matched the literal string **"In-Office"**, flagging San
Francisco roles as India. It reported "+47 postings recovered" and my summary
line printed **HOLDS**. All 47 were false positives.

Corrected, case-sensitive rule over 4,337 real postings:

- plain city-list match: **167** postings
- buggy rule: 214 (+47, **all junk** — only 2 distinct strings, `In-Office` and `Hybrid; In-Office`)
- corrected rule: **167** (+0 real gain)

**So the ISO-prefix rule is unnecessary — delete it.** A plain city-name list
already catches everything real, including Ashby's `IN-Pune` (because "pune" is
in the list). Simpler *and* correct.

Location formats that must be handled: `Bengaluru, India`, `Remote - India`,
`India - Remote`, `IN-Pune`, and **multi-city single postings** like
`Bengaluru, India; Mumbai, India` (7 seen). Ashby also has a `secondaryLocations`
array that must be read, or multi-location roles are undercounted.

Residual known gap: a city absent from the list inside an `IN-<City>` string
would be missed. Measured occurrences: 0. Accepted for now.

## 3. ATS slug discovery — works ~50%, needs both methods

- Regex the company's careers page for board URLs: **4/7**. Misses JS-rendered
  pages (Anthropic, Glean both returned 200 with no board link in the HTML,
  despite both genuinely being on Greenhouse).
- Guess the slug from the company name and probe Greenhouse directly: **4/8**,
  and it costs ~0.3s per guess, so guessing is nearly free.

Neither alone is enough; together they cover most, and a hand-maintained
override list is needed for the tail. This is presumably why the reference site
hardcodes `ats` and `ats_slug`.

## 4. MCA — the staleness fear was half right, and it matters

**All 37 state-wise "Company Master Data of \<State\>" datasets are capped at
"upto 31st March 2021".** Five-plus years stale. Building on them would produce a
site blind to every company incorporated since 2021 — exactly the cohort of
interest. **These are the obvious datasets and they are a trap.**

The exception, and the only usable source found:

```
Title  : Registrars of Companies (RoC)-wise Company Master Data
Index  : 4dbe5667-7b6b-41d7-82af-211562424d9a
Rows   : 3,674,314  (company-level, not aggregates)
Updated: 2026-07-22
Fields : CIN, CompanyName, CompanyROCcode, CompanyCategory, CompanySubCategory,
         CompanyClass, AuthorizedCapital, PaidupCapital,
         CompanyRegistrationdate_date, Registered_Office_Address, Listingstatus,
         CompanyStatus, CompanyStateCode, CompanyIndian/Foreign Company,
         nic_code, CompanyIndustrialClassification
```

Newest registration date observed: **2026-03-31**, sampled across five offsets
spanning the table. Roughly four months' lag. Genuinely current.

Access notes:
- `data.gov.in` returns **200 to plain curl**. My earlier "geo-blocked" call was
  wrong — headless Chromium is bot-fingerprinted and 403s, curl does not. Probe a
  403 with two clients before believing it.
- `mca.gov.in` itself is genuinely 403. Assume no access.
- `api.data.gov.in` works with the published sample key.

### RESOLVED with a registered key (2026-07-28)

All three questions answered. A registered key changes the picture completely.

**1. Page size: 10,000 per call** (sample key was capped at 10). Verified at
10 / 100 / 1000 / 5000 / 10000 — each returned exactly what was asked for.
Full scan of 3,674,314 rows = **367 calls**, not 367,431. Bulk pull is trivial.

**2. Subcategory: the value exists, I just had the wrong string.**

| my guess | reality |
|---|---|
| `Subsidiary of Foreign Company` | `subsidiary of company incorporated outside India` |

So the `total=0` was a **genuine zero, not throttling** — I was querying a value
that doesn't exist. Server-side count for the real value:

```
CompanySubCategory = "subsidiary of company incorporated outside India"
  -> total = 24,102
```

**That is the MCA enrichment universe: 24,102 foreign-subsidiary companies.**

Observed `CompanySubCategory` distribution over a 6,000-row sample:
`Non-government company` 4,967 · `(empty)` 991 ·
`subsidiary of company incorporated outside India` 35 ·
`Guarantee and association Company` 4 · `State government company` 2 ·
`Union government company` 1.

**3. `CompanyStateCode` is OPTIONAL, not mandatory** despite the metadata's
`mandatory: True`. Unfiltered query returns the full 3,674,314. State filters
work as a convenience for sharding (karnataka 258,322 · maharashtra 755,653 ·
delhi 507,637 · telangana 219,893 · tamil nadu 251,291).

### Do NOT use `CompanyIndian/Foreign Company` — the field is corrupt

Observed values: `India` (2,455,242), **`91` (668,674)**, `(empty)`,
`Australia` (91). A phone country code has leaked into a country field across
~670k rows. Use `CompanySubCategory` for the foreign-subsidiary signal and treat
this column as unusable.

### Operational constraint: the API is flaky under sustained load

After roughly 20 successful calls, **every** request began returning HTTP 502 —
including unfiltered `limit=10`, which had worked moments earlier. Not a
page-size issue and not specific to filtered queries; the whole resource went
dark. The metadata exposes an upstream Elasticsearch (`10.193.68.52:9200`), so
this is plausibly the backend rather than a rate limiter.

Consequences for the build: the MCA pull needs retry with real backoff, must
tolerate a dead upstream without failing the whole run, and — since it only
needs to happen occasionally — should write to a **cached local snapshot** that
the nightly job reads rather than re-fetching. 367 calls, run rarely, cached.

---

## What this changes for the spec

1. **Greenhouse-first.** It's fast, complete and honest. Ashby second, on a
   separate slower schedule with backoff. Lever last, with its zero-result
   ambiguity handled explicitly.
2. **Drop the ISO-prefix regex.** City-list matching only.
3. **Refresh budget is set by Ashby**, not by anything else: ~4.7h per 1000
   Ashby companies at concurrency 12.
4. **MCA is a deferred enrichment bead**, blocked on one cheap human action
   (get an API key), and it must use the RoC dataset — never the state-wise ones.
5. **No freshness figure belongs in the spec** beyond what's measured here.

---

# FinSMEs scraping — measured during T1.1 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/finsmes_live.py`.

## Python cannot fetch finsmes.com. curl can.

`urllib.request.urlopen` **hangs indefinitely** against `finsmes.com` — past a
15s `timeout=`, past 60s wall. The socket timeout never fires because the
connection is accepted and then simply never answered. curl fetches the same URL
in ~4.4s over both HTTP/1.1 and HTTP/2.

Cloudflare is fingerprinting the TLS handshake, so this is not fixable with
headers and would not be fixed by `requests` either (same OpenSSL fingerprint).
`src/finsmes.py:fetch` shells out to curl. Do not "clean this up" back to
urllib — it will hang the nightly run rather than fail it, which is worse.

## Two more traps on the same host

| Thing | Result | Consequence |
|---|---|---|
| curl's default UA | **403** | a browser UA is load-bearing, not decoration |
| `HEAD` on an article URL | **403** | a HEAD-based liveness check reports every good source URL as dead. Use GET with the body discarded. |
| `GET` on the same article URL | 200 | |

## Pagination is blocked; only bare category pages are reachable

`/category/usa` returns 200 reliably. `/category/usa/page/2/`, `/category/uk`
and `/category/india` all return Cloudflare's "Just a moment..." interstitial
(403, ~5KB), including with full browser headers and `--retry`.

**Consequence for T1.5 (≥1,000 distinct companies): FinSMEs yields ~12 records
per reachable page, and right now exactly one page is reachable.** FinSMEs alone
cannot reach 1,000. That target depends on T1.2/T1.3/T1.4 (YC, SEC Form D,
TC/Forbes/CBI) — SEC EDGAR in particular is a bulk API with no bot wall and is
the realistic source of volume. Do not plan T1.5 around crawling FinSMEs deeply.

## Headline grammar (12 live headlines, one page)

Two verbs observed: `Raises` (8), `Receives` (4).

```
CORE Biomedicine Raises $21M in Series A Funding
PawPay Receives Investment From VANE
```

Amount and round letter come from the headline; the date comes from the
listing's `<time datetime="...">`; the source URL is the article link. No
article fetch is needed for a complete record.

Scales seen: `$700K`, `$7.25M`, `$170M` — decimals are real, and `K` must not be
read as `M`. Rounds without a letter are real and common (`Seed`, `Pre-Seed`,
`Seed Extension`) and must yield `round_letter=None` rather than a guess.

`COR Receives Investment From FTV Capital` is a real company called COR, not a
truncation bug. It looks exactly like one next to `CORE Biomedicine`.

## Qualification yield — measured during T1.5 (2026-07-28)

Running the live category page through merge/qualify: **12 records → 7 qualified
(6 by letter, 1 by amount), 5 unqualified**. So **~42% of headlines state neither
a round letter nor an amount** and cannot be judged either way.

Consequence for sizing T1.2/T1.3/T1.4: raw record count is not corpus count.
Reaching 1,000 qualified companies needs roughly **1.7× that many raw records**,
before any cross-source dedup takes its own cut. EDGAR is the source to lean on —
Form D states the amount structurally rather than in prose, so its yield should be
far above 58%; that is worth measuring rather than assuming when T1.3 lands.

---

# Careers-page slug discovery — measured during T2.1 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/careers_slugs_live.py`.

## 5/7 by name, up from the 4/7 baseline — and trying `/jobs` is why

Resolving the same 7 companies §3 used, but starting from **the name alone**
(guess the domain, then regex the careers page) rather than from a hand-written
careers URL:

| company | outcome |
|---|---|
| Anthropic | greenhouse/anthropic |
| Figma | greenhouse/figma |
| Ramp | ashby/ramp |
| Vercel | greenhouse/vercel |
| Razorpay | greenhouse/razorpaysoftwareprivatelimited |
| Glean | `no-board-link` |
| Postman | `no-board-link` |

**§3 was wrong about Anthropic.** It is not that the page is JS-rendered — it is
that `/careers` is a *marketing* page and the board lives one level deeper.
`anthropic.com/jobs` redirects to `/careers/jobs`, which carries 1,355 plain
`job-boards.greenhouse.io/anthropic` links in the HTML. Two consequences:

- **Try `/jobs` as well as `/careers`.** It is also the only thing that reaches
  CORE Biomedicine, whose `/careers` 404s while `/jobs` is a real 130KB page.
- **Follow redirects** (`curl --location`). Every win above went through at least
  one redirect — bare domain → www, or `/jobs` → the real listing path.

Glean and Postman are genuine `no-board-link`: real careers pages, no board URL
in the HTML. That is T2.2's territory, and it is why the reason vocabulary
distinguishes "never reached a page" from "read the page, no board on it".

## A parked domain answers 200, and it will lie to you

`antareslabs.com/careers` returns **HTTP 200 with 114 bytes**:

```html
<!DOCTYPE html><html><head><script>window.onload=function(){window.location.href="/lander"}</script></head></html>
```

A domain squatter, not the company. Taken at face value this records
`no-board-link` — *"we read Antares Labs' careers page and it linked no board"* —
about a company we never reached. `src/slugs.py` therefore floors the body at
2,000 bytes. The smallest **real** careers page measured in this sample is 130KB,
so there are three orders of magnitude of headroom and the threshold is not
delicate.

## The rate is 71% on known companies and 0% on the actual corpus

Running the real corpus (7 FinSMEs companies, all freshly-funded and obscure):
**0/7 resolved** — 5 `no-careers-page`, 2 `no-board-link`.

This is not a bug and the numbers do not contradict each other. The 50% baseline
was measured on companies whose name maps cleanly onto their domain
(Figma → figma.com). Newly-funded companies mostly do not: "Alpen High
Performance Products" is not `alpenhighperformanceproducts.com`, and several
have no public ATS board at all yet.

**The domain guess is the binding constraint, not the board regex.** The regex
found every board that was actually on a page it reached. What is missing is a
real website field — which **T1.2 (YC) and T1.3 (EDGAR) both carry**. Feed that
in and this method's ceiling rises without touching the extraction at all. The
residual tail is T2.3's override file.

Worth stating plainly for whoever sizes Phase 1: **a name-guessed domain is
unverified**. Reaching a 200 does not prove the site belongs to the company. The
length floor catches squatters; it does not catch a legitimate different company
at the same name. A real website field removes that whole class of error.

---

# Greenhouse probe — measured during T3.1 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/greenhouse_live.py`.

## §1's meta.total claim still holds, on boards 4× bigger than when it was made

Same 5 slugs, re-measured today, `meta.total` compared against the returned
count on a raw response:

| slug | roles | meta.total |
|---|---|---|
| databricks | 801 | 801 |
| anthropic | 415 | 415 |
| gleanwork | 104 | 104 |
| togetherai | 59 | 59 |
| figma | 177 | 177 |

Exact on all five, at 801 roles in a single unauthenticated call. There is no
pagination to walk and no page-size ceiling in sight. Anthropic's board has gone
from the 1,355 job links seen on its careers page (§T2.1) to 415 open roles —
the careers-page link count is not a role count, and nothing should read it as
one.

**A wrong Greenhouse slug 404s.** Verified against a nonsense slug: HTTP 404,
not a 200-with-empty-array. That is precisely the distinction Lever cannot make
(§1), and it is why a Greenhouse board returning zero roles is trustworthy as a
real zero while a Lever one is `empty-board-unverified`. Do not generalise the
Greenhouse handling to Lever — the two look identical and mean opposite things.

## curl's exit code is not enough to tell a 404 from a 502

`src/net.py` originally used `curl --fail`, which collapses every non-2xx into
one "no page" signal. T3.1 needs the two apart: a 404 means T2.1 resolved the
wrong slug (`slug-unresolved`, a fixable data problem) while a 502 means we
failed to read a board we may well own (`probe-failed`, a retry). `net.get` now
returns `(status, body)` via `--write-out %{http_code}` and `fetch` is a thin
wrapper over it. Status `0` means the transfer never happened at all — curl
writes `000` for DNS failure, refused connection and timeout alike.

Consequence for the remaining probes: **T3.2 and T3.3 should use `net.get`, not
`net.fetch`.** Both need the status to classify an outcome honestly, and both
have a silent-failure mode that a boolean "did we get a page" hides.

---

# India matcher — measured during T3.4 (2026-07-28)

## Word boundaries are free, and they close a trap the substring rule left open

§2 established the rule (city list, no ISO regex). `src/india.py` matches those
same city names with `\b` boundaries rather than plain `in` substring tests.
Compared over **1,497 live Greenhouse postings** (databricks, anthropic,
gleanwork, figma), the two rules agree exactly:

```
boundary rule: 104   substring rule: 104
lost by boundaries: []   gained: []
```

So the boundaries cost nothing real, and they buy `Indianapolis, Indiana`
(`india` is a substring of `Indiana`) and `Thanet, UK` (`thane`). Neither appeared
in this sample, which is the point: the substring rule was *unfalsified*, not
correct, and a single US-Midwest posting would have shipped as an India role.

The corollary is that this class of bug is invisible in aggregate counts. §2's
own precision bug was caught by looking at the *distinct strings* a rule admitted,
not at how many it admitted. Any future widening of `CITIES` should be checked the
same way.

## Redundant city entries were dropped

`navi mumbai` is removed from the list in §2: `mumbai` already matches it, and a
second alternative that can never fire alone is dead code in a regex.

---

# Build spine — measured during T5.1 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/build_live.py`.

## `location.name` is present and a string on all 1,556 live roles

The spine unwraps a Greenhouse role as `(role.get("location") or {}).get("name")`.
If a live board carried a null or differently-shaped location, those roles would
quietly fail the India test — an undercount indistinguishable from a correct
answer, which is this project's signature failure mode.

| slug | roles | India | location not a dict | name not a string |
|---|---|---|---|---|
| databricks | 801 | 77 | 0 | 0 |
| anthropic | 415 | 3 | 0 | 0 |
| gleanwork | 104 | 21 | 0 | 0 |
| togetherai | 59 | 3 | 0 | 0 |
| figma | 177 | 3 | 0 | 0 |

**0 exceptions in 1,556 roles**, and **5/5 boards produce a listed row**. So the
one-line unwrap is safe for Greenhouse, and a non-empty `companies.json` is
demonstrated against live data. Ashby's role shape is a different question and
belongs to T3.2 — it has a flat `location` plus `secondaryLocations`, so it will
need its own unwrap, not this one.

Note the India counts are a *fraction* of each board (77/801 is Databricks' best
showing here). Nothing about "a funded company" implies "hiring in India", which
is the whole reason the site probes rather than claims.

## `companies.json` is empty today, and that is the corpus, not the emitter

A full real build right now: **7 corpus companies → 0 listed, 7 slug-unresolved.**
`data/slugs.json` is `{}` because T2.1 measured 0/7 on this corpus — freshly-funded
obscure companies whose names don't map onto their domains (T2.1 §"The rate is 71%
on known companies and 0% on the actual corpus").

So the chain is intact and the input is thin. The same shape as T1.5's >=1,000
line: **T1.2 (YC) and T1.3 (EDGAR) carry a real website field**, which raises slug
resolution, which is the only thing standing between this emitter and a populated
site. Nothing in T5.1 needs to change when that lands.

---

# The site — measured during T5.2 (2026-07-28)

## A `file://` page cannot `fetch()` the JSON next to it

The gate drove `file://$(pwd)/site/index.html` because that needed no server.
Measured: the page loads, and the fetch fails outright —

```
[error] Fetch API cannot load file:///tmp/fetchprobe/d.json.
        URL scheme "file" is not supported.
```

No header or flag fixes that from inside the page; it is Chromium's scheme rule.
So `scripts/e2e.sh` serves the repo over `python -m http.server` on 127.0.0.1 and
drives `http://`. That is also the deployment we ship (GitHub Pages is HTTP), so
the gate now exercises the real loading path rather than a local-only one.

Corollary worth keeping: the tempting fix — emit a `site/data.js` that assigns
`window.COMPANIES` — would have worked on `file://` and cost a second copy of the
published data. A server is cheaper than a second source of truth.

## A missing favicon is a failed network request

`console-clean` asserts zero non-2xx responses, and a page with no `<link
rel=icon>` makes Chromium request `/favicon.ico` and get a 404. The site carries
`<link rel="icon" href="data:,">` for exactly that reason. Any new page in this
repo needs the same line or the gate will fail on a file nobody meant to request.

## `browse` quirks the e2e is built around

Measured while wiring layer 4, all three of which cost a debugging cycle:

| Thing | Behaviour | What the e2e does |
|---|---|---|
| `browse click <sel>` with a selector matching >1 element | refuses: "Selector matched multiple elements" | `.row:first-of-type summary` |
| `browse fill <sel> ''` | rejected, "Usage: browse fill <selector> <value>"; the old value stays | search checks run LAST, so nothing needs clearing |
| two `browse` daemons alive at once | commands split across two browsers; the symptom is row diffs that read exactly like site bugs | `open_page` asserts `location.href` is the URL it asked for and says "try: browse stop" |

## A collapsed `<details>` is in the DOM and has a bounding box

Rows are native `<details>`/`<summary>` disclosures — no click handler, no
`aria-expanded`, keyboard-reachable for free. But asserting "the detail is
hidden" cannot use `querySelector` (it matches when closed) or `offsetHeight`
(112px when closed, same as open). `checkVisibility({contentVisibilityAuto:
true, visibilityProperty: true})` is the one that reports `false` closed and
`true` open. A weaker assertion here would have passed against a row whose detail
was permanently unreachable.

## The gate was broken on purpose, three ways, before being believed

Per VERIFICATION.md's "only once the gate has caught at least one real failure":

| Injected bug | Caught by |
|---|---|
| city filter keeps any company with *any* city | `filtering to a city…` — expected `Gamma Health\|Acme Cloud`, got the Pune-only company too |
| a stray undefined function call at load | 12 checks failed, starting with `zero console errors` |
| snapshot date never written to the DOM | `snapshot date is visible` — expected `2026-07-28`, got `—` |

## `cities` is now in the schema, and why that landed here rather than in T4.1

T5.2's own DoD requires `e2e:filter_city_returns_only_matching`, and a city
filter cannot be verified — or built — without city data. Schema v1 had none:
T3.4 deliberately left "which cities they are" to T4.1, which the graph places
two phases later. Rather than test the filter against a fixture shape the emitter
could never produce, `src/india.py:cities` and row field `cities` landed here and
`SCHEMA_VERSION` went to 2. **T4.1 keeps role titles, apply URLs and the explicit
remote flag; its `test_city_and_remote_parsing` will find the city half already
done.** Search before rebuilding it.

Two things fell out of writing it:

- **Alias collapsing is load-bearing for a filter, not cosmetic.** `CITIES`
  carries both spellings of six cities (bengaluru/bangalore, gurgaon/gurugram,
  kochi/cochin, trivandrum/thiruvananthapuram, mysore/mysuru,
  vizag/visakhapatnam). Left alone, the site offers "Bangalore" and "Bengaluru"
  as two places and each hides the other's roles. `india.ALIASES` maps variants
  onto one canonical name.
- **An India role with no named city is a real answer.** `Remote - India` yields
  `cities: []`, which is not missing data. The site renders it "India — city not
  stated"; an empty cell would read as a bug and a fabricated city would be a lie.

## Visual regression (VERIFICATION 4c) is deliberately NOT in the gate

It needs baseline screenshots a human approves once. An agent that approves its
own baselines asserts nothing, so this is left outside the gate and named here
rather than faked inside it. Everything else in layer 4 (4a console-clean, 4b
behavioural, 4d a11y basics) runs.

---

# YC directory — measured during T1.2 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/yc_live.py`.

## YC's own API cannot qualify a single company; the mirror can

Two endpoints serve the same 6,087 companies, and only one is usable here:

| Source | Calls | Carries `stage`? |
|---|---|---|
| `api.ycombinator.com/v0.1/companies` (official) | **244** (25/page) | **no** |
| `yc-oss.github.io/api/companies/all.json` (mirror) | **1** (10.2MB) | yes |

The official API takes `batch=` and `status=` as filters but not `stage=`, and
`stage` is absent from every record it returns. That matters more than call
count: **`stage` is the only fundedness signal YC publishes.** The directory
states no amount, no round letter and no round date for anybody, so without
`stage` all 6,087 records are unqualifiable and the source contributes nothing.
So the mirror is not a convenience here, it is the only version of this source
that works — first-party is the wrong tradeoff when first-party omits the field.

`ponytail:` ceiling — the mirror is one person's GitHub Pages build of YC's
Algolia index (`last_updated` was the morning of this run). If it goes stale or
away, the upgrade path is the Algolia index directly, whose keys are in the
`ycombinator.com/companies` HTML. Not worth doing before it breaks.

## `Growth` means past Series A, and it checks out on every name I know

`stage` has exactly two values over 6,087 records: `Early` 5,012, `Growth` 1,075.
Spot-checked against companies whose funding history is public:

```
Growth: Stripe · Airbnb · Razorpay · Groww · Zepto · Meesho · Instacart
        Coinbase · Rappi · Flexport · Brex · Deel · Vanta · Whatnot
Early:  Conifer (S26, team of 3)
```

No misclassification found in either direction. So `Growth` is read as
qualifying evidence — SPEC feature 2's third rule, `qualified_by: "stage"`,
alongside `letter` and `amount`. **This extends SPEC feature 2, which named two
rules.** The alternative was to record `round_letter="A"`, which invents a round
YC never stated, or to drop the source, which throws away the only evidence it
has. Flagged for the human; nothing else in the build changes if it's reversed.

## What a directory source cannot say, and what that cost

YC states **no round date**. A batch date is not one — reading `Winter 2015` as
Razorpay's funding date would rank it under "recently funded" by when YC first
wrote a cheque, and sort Stripe by 2009. So `date` is `None`, which pushed
`Record.date` and the published schema to nullable (**schema v3**), and the site
now renders `date not stated` and **excludes undated rows from the recency
filter** — an absent date can't satisfy "funded in the last 90 days".

Same shape as `cities: []` in T5.2: the absence is a real answer, not missing data.

## Two bugs the gate caught, one of which was already live

Per VERIFICATION's "only once the gate has caught a real failure":

| Injected bug | Caught by |
|---|---|
| `announced ${c.date}` instead of `when(c)` | `an absent fact never renders as null` — got 1 row reading "announced null" |
| undated row treated as funded on the snapshot date | `an undated company is not claimed as recently funded` — Epsilon Directory appeared under "last 90 days" |

And one that was **not injected**. The e2e reported `../data/companies.json is
v2` while the file on disk was v3, twice, after a clean rebuild. Chromium was
serving the JSON from cache: neither the page nor the file carries
`Cache-Control`, so a browser is free to invent a freshness lifetime and pair
yesterday's data with today's renderer. `site/index.html` now fetches with
`{cache: 'no-cache'}` — revalidate always, a 304 still keeps the bytes. This was
a **production** bug on a site whose entire claim is "as of the snapshot date",
and the only reason it surfaced is that a schema bump made stale data *loud*.
Any future check that reads a committed JSON through a browser should assume the
same trap.

## The corpus is now 1,081 and slug resolution is the new wall

```
corpus.json: 9 -> 1081 qualified (1072 stage, 6 letter, 3 amount), 4916 unqualified
```

**The >=1,000 line that T1.5 relocated to the Phase 1 sources is met by T1.2
alone** — before EDGAR, which was expected to carry it. T1.3/T1.4 now widen a
corpus that already clears the bar rather than rescuing one that doesn't.

The binding constraint moved. Careers-page slug resolution on 20 random YC
Growth companies: **2/20 (10%)**, 60s wall at 8 workers — so ~3s/company, ~54
minutes for the full 1,081, and `data/slugs.json` was deliberately NOT
regenerated in this iteration. The failures split 10 `no-careers-page` / 8
`no-board-link`.

That 10 is the interesting half, and it is **fixable data, not a hard limit**:
`src/slugs.py` guesses the domain from the company name because no source
carried one, and **the YC payload has a `website` field on 1,072 of the 1,075
Growth companies**. `src/yc.py` does not read it today — deliberately, because
nothing consumes it yet (`slugs.resolve` takes a name, not a record). Wiring it
is one line in `yc.parse`, one field on `Record`, and threading the company
rather than the name through `resolve`/`resolve_all`. **That is the single
highest-value change available to T2.2/T2.3**, and it is measured rather than
assumed: half the current failures never reached a page at all.
