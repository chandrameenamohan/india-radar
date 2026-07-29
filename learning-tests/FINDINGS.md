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

---

# SEC Form D — measured during T1.3 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/edgar_live.py`.

## The UA that works everywhere else gets a blanket 403 here

`net.UA` — the browser string that is load-bearing against Cloudflare on
FinSMEs — returns **403 on every sec.gov URL tried**: the data sets, the
full-index files, `cgi-bin`. SEC's automated-access policy wants a declared
contact instead, and enforces it:

| UA | result |
|---|---|
| `Mozilla/5.0 ... Chrome/126.0 ...` | **403** |
| `india-radar chandra@hakimo.ai` | **200** |

So `net.get_bytes` grew a `ua=` parameter. One host's requirement is another
host's block, and there is no single string that satisfies both.

## The bulk data set, not 16,000 filings

SEC republishes each quarter's Form D as a zip of TSVs — `ISSUERS` and
`OFFERING`, joined on `ACCESSIONNUMBER`. One call, 3.6MB, ~15,700 filings. The
per-filing route (`primary_doc.xml`) is the same data at ~16,000 requests.

**The path is `files/structureddata/data/form-d-data-sets/`, not `files/dera/...`** —
the `dera` spelling 404s.

## Publication lag is real and is not a fixed number of months

On 2026-07-28, four weeks after Q2 closed:

```
2026q3 404 · 2026q2 404 · 2026q1 200 · 2025q4 200 · 2025q3 200 · 2025q2 200
```

2026Q1 had been up since 3 April. So the newest quarter **cannot be computed
from today's date** — `edgar.quarters()` offers `QUARTERS + 3` candidates newest
first and lets the 404s choose. Anything that assumes "current quarter minus
one" builds an empty corpus for weeks at a time and reports it as success.

## A naive Form D scrape builds a directory of venture funds

This is the finding that matters. Of 15,981 issuer rows in 2026Q1:

| dropped | why |
|---|---|
| 5,765 | amendments (`D/A`) restating a round already counted |
| 5,757 | pooled investment funds — **Bain's and Sequoia's own funds file Form D** |
| 3,360 | not technology: real estate, oil and gas, REITs, restaurants, biotech |
| 247 | co-issuers on someone else's raise (`IS_PRIMARYISSUER_FLAG = NO`) |
| **852** | **technology operating companies — what we keep** |

Of those 852, **247 clear the $5M proxy**. So ~1.6% of a quarter's Form D
filings are companies this site would ever list. Filtering is not tidying here;
without it the corpus is 64% venture funds, none of which hire engineers.

Form D's industry taxonomy has **no "Software" value** — its entire technology
branch is `Computers`, `Other Technology`, `Telecommunications`.

## Fields: what Form D states and what it doesn't

- `TOTALAMOUNTSOLD`, not `TOTALOFFERINGAMOUNT`. The latter is the ceiling the
  filer may raise and is routinely open-ended; the former is money in the door.
  `0` is a real answer (announced, nothing closed yet), not missing data.
- `SALE_DATE` is ISO and present on **all 247** qualifying rows. `FILING_DATE`
  is `31-MAR-2026`, not ISO — don't reach for it without converting.
- **No round letter, ever.** Form D states dollars. So every EDGAR record
  qualifies by `amount`, never by `letter`.
- Source URL `…/Archives/edgar/data/{int(CIK)}/{accession-no-dashes}/{accession}-index.htm`
  — verified 200 on five sampled filings. CIK is zero-padded in the TSV and
  unpadded in the path.

### EDGAR does NOT carry a website field — correcting T2.1 and T1.2

Both `src/slugs.py`'s ponytail comment and T1.2's FINDINGS entry say "T1.2 (YC)
and T1.3 (EDGAR) both carry a real website field". **Measured: EDGAR does not.**
`ISSUERS.tsv` has street, city, state, zip and phone, and no URL column of any
kind. The YC half of that claim stands (1,072 of 1,075). Whoever picks up T2.2
should size it on YC alone.

## EDGAR files a registry name; every other source publishes a company name

244 of 247 qualifying names carry a legal suffix — `Legora, Inc.`,
`SOLIDROAD INC.`, `Core Foundry Labs, LLC`. Under `corpus.py`'s dedup key
(casefold, drop non-alphanumerics) that is a **different company** from YC's
`Legora`, so the corpus would list both.

`corpus.py` had already named this as the trigger: *"add suffix stripping when
T1.2–T1.4 produce a duplicate this misses."* Measured, it does — so the strip
went in `edgar.py`, at the source, rather than in the shared key:

| approach | cross-source merges | false collapses |
|---|---|---|
| plain key, name as filed | 0 | 0 |
| plain key, suffix stripped **at the source** | **5** | **0** |
| shared key strips descriptive words too (`technologies`, `holdings`) | 6 | risks `Garage` ≡ `Garage Technologies` |

Stripping at the source also fixes what the shared-key version would not: the
merged row keeps the *clean* name, and `slugs.py` guesses a domain from the
name — `legora.com` resolves, `legorainc.com` does not. Trailing legal wrappers
only; descriptive words are part of what a company is called.

## The bug adding a second amount-bearing source introduced

`corpus._strength` picked the record with the biggest number. YC calls Lob
`Growth`; EDGAR reports Lob filing a $2M round. Both are true — but the $2M
record won and then failed the $5M proxy, so **a company past Series A left the
corpus because a second source mentioned a small raise.**

Measured: 4 real companies (Datafold, Legion Health, Lob, Overview) were
demoted from qualified to unqualified purely by adding EDGAR.

`_strength` now ranks `_qualified_by(record) is not None` first — qualifying
evidence outranks a bigger number; everything else is unchanged. Two sources
describing one company are **complementary, not contradictory**, and the merge
must not discard one source's qualifying evidence because another mentioned a
smaller round. `test_a_small_recent_round_never_disqualifies_a_company_another_source_qualifies`
was confirmed to fail with the old ordering restored.

**Generalises to T1.4:** any further amount-bearing source can demote companies
the same way. The invariant to check is not "did the corpus grow" (it grew by
976 while losing 4) but "did anything qualified leave".

## Corpus after T1.3

```
1,081 -> 2,054 qualified   (+973 new, 0 lost)
qualified_by: stage 1,059 · amount 989 · letter 6
unqualified:  4,916 -> 6,974
```

A year of filings — `QUARTERS = 4`, so a spring round is still in the corpus and
2019's is not. `data/slugs.json` was **not** regenerated (unchanged from T1.2's
reasoning: ~3s/company, and the corpus just doubled), so `data/companies.json`
is untouched and the site still renders T1.2's snapshot. Slug resolution remains
the binding constraint on site size, and it is now against 2,054 companies.

---

# T1.4 — TechCrunch, Forbes, CB Insights (2026-07-28)

All three are reachable and all three are **structural**, which was not the
expectation going in. The surprise is that two of them state no round at all.

## What each source actually states

| source | route | what it states | qualifies by |
|---|---|---|---|
| TechCrunch | WordPress REST API, 100 posts/call | a round: money, sometimes a letter, a date | `amount` / `letter` |
| Forbes | `forbesapi/org/<list>/<year>/position/true.json` | **cumulative** funding, $M | `stage` |
| CB Insights | one server-rendered HTML page | a **valuation**, $B | `stage` |

## Neither Forbes nor CB Insights states a funding round

Forbes' `funding: 830` is $830M raised across Abridge's whole life — there is no
letter, no round size and no round date anywhere in the payload. CB Insights'
`$965` is what Anthropic is *worth*, and its "Date Joined" column is the day the
company first crossed $1B, not its latest round.

Putting either number in `amount` would report a round nobody raised and hand
SPEC feature 2's $5M proxy a figure it was not written for. So both carry
`stage="growth"` instead — T1.2's third rule, unchanged, doing exactly the job it
was added for. **No fourth qualification rule was needed.**

For Forbes the stage claim is gated on the total being stated at all, because
the zeroes are real: Forbes reports `funding: 0` for **Midjourney, Surge AI,
Hyperliquid and Increase**, and no funding field for **Zoho** — the bootstrapped
companies, correctly identified. A total Forbes does not state is not evidence
of a Series A, so those five leave by `corpus.py`'s counted door.

## A naive TechCrunch scrape builds a directory of VC firms and sentence fragments

Measured over 1,000 live venture posts (`categories=577030455`, ~17 months):
**77 headlines announce a round.** A plain `^(name) raises` on them yields:

- four VC firms raising their own funds — Accel, Lightspeed, CRV, SignalFire
- a company called `Edtech platform` (the headline never names it)
- a company called `Gen Zers`, from *"…, founded by two Gen Zers, raises $22M"*
- `Crypto VC firm Paradigm`, `Seedcamp`, `Benchmark`, `Menlo Ventures` — funds

This is EDGAR's pooled-investment-fund lesson again: the venture category covers
the *industry*, not only the companies in it. Three structural rules, not a name
list, get it to 69 clean records:

1. **The name is the trailing proper-noun run** of what precedes the verb.
   TechCrunch writes sentence-case prose with the descriptor first — `Amazon
   fulfillment competitor Stord` → `Stord`, `Edtech platform` → nothing.
2. **A clause closing on a comma right before the verb is grammar, not a name.**
   Kills the `Gen Zers` class outright.
3. **A fund raise is rejected**: `fund(s)`, `VC`, `venture capital/firm`, `LPs`,
   `fresh capital`, `to back`, `to invest in`, or a name ending `Ventures` /
   `Capital` / `Partners` / `Fund` / `Management`.

**A valuation is not a round.** `raises $250M at $3B valuation` is a $250M round,
and `Glean lands a $7.2B valuation` is no round at all. The parser takes the
first money figure *not* followed by `valuation` / `valuing` / `ARR` / `revenue`;
where that leaves nothing, the record needs a stated letter or it is dropped.

Known residue, accepted and measured: 1 in 77 absorbs a one-word capitalised
descriptor (`How Lucra`), because the first word of a headline is capitalised for
being first. Lerer Hippeau (a fund, phrased with none of the signals above) also
gets through. Both then fail slug resolution and are counted, rather than
appearing wrongly on the site.

## Two structural filters that did NOT work

- **Requiring `category-startups`** (present on the class_list of company posts,
  absent from the fund posts) looked like the clean EDGAR-style flag. Measured,
  it drops 19 of 77 records to kill 4 VC firms — 15 real companies for 4 junk
  rows. Rejected; the regex filter above is strictly better here.
- **Matching `Ventures|Capital|Partners` anywhere in the title** rejects real
  companies, because those words are in the *investors'* names —
  `Infinity raises $15M from Touring Capital` is a real company. The firm-suffix
  test only runs against the extracted company name.

## TechCrunch throttles paging, intermittently and without a 429

Walking 12 pages back-to-back: page 11 returned **403** and page 12 returned 200.
Roughly one page in ten, no pattern, and the failure is a 403 rather than a 429
or a `Retry-After`. So `techcrunch.download()` retries a page once and then keeps
walking — stopping at the first failure silently halves the source, which is how
a first attempt at this fixture came back with 7 of 11 posts and no error.

## CB Insights: the whole unicorn board is one unpaywalled server-rendered page

1,404 companies with valuation, date joined, country, city, industry and a
profile link that resolves 200 — no key, no pagination, no JS. The industry
column is the source's own, and SPEC's non-goals applied to it drop 553:
Industrials 213, Consumer & Retail 209, Healthcare & Life Sciences 128 (plus 3
rows of data noise: `Industrial`, `Health`, `West Palm Beach`). **851 kept.**
Unfiltered, this source's largest contribution to a site about software jobs
would be manufacturers and biotechs.

Company profile slugs are not derivable from names — SingleStore files under
`/company/memsql` — so the link is read from the row, never rebuilt.

## Corpus after T1.4

```
2,054 -> 2,953 qualified   (+899 new, 0 demoted)
qualified_by: stage 1,897 · amount 1,040 · letter 16
contributing the winning record: YC 1,051 · EDGAR 985 · CB Insights 683 ·
                                 Forbes 163 · TechCrunch 63 · FinSMEs 8
```

Each source alone, against a corpus rebuilt live from T1.1–T1.3: CB Insights
+784, Forbes +166, TechCrunch +53. Re-run with
`.venv/bin/python learning-tests/t14_sources_live.py` — the baseline is rebuilt
from the earlier sources rather than read from `data/corpus.json`, because once a
build has run that file already contains all six and the comparison answers
itself.

The whole six-source corpus build is **44 seconds**. Nothing here is the
expensive part of this project.

`data/slugs.json` was **not** regenerated — unchanged from T1.2's and T1.3's
reasoning (~3s/company against a corpus that grew another 44%), so
`data/companies.json` is untouched and the site still renders T1.2's snapshot.
Slug resolution is now the binding constraint against 2,953 companies, and every
source that could widen the corpus has landed. **T2.2 is the next real gain.**

---

# Slug guessing — measured during T2.2 (2026-07-28)

Re-run with `.venv/bin/python learning-tests/slug_guess_live.py`.

## The 8-company fixture: 6/8 by careers-page, 8/8 combined

```
Anthropic  greenhouse/anthropic (careers-page)   Glean    greenhouse/gleanwork (guess)
Figma      greenhouse/figma     (careers-page)   Postman  greenhouse/postman   (guess)
Ramp       ashby/ramp           (careers-page)   Vercel   greenhouse/vercel    (careers-page)
Notion     ashby/notion         (careers-page)   Razorpay greenhouse/razorpay… (careers-page)
```

**The DoD names Anthropic and Glean as the two that must come back through
guessing. Live, only Glean does** — Anthropic has resolved by careers-page since
T2.1 started trying `/jobs`, which is measured in this file above. Postman took
its place, so the pairing holds in shape (two JS-rendered boards recovered) and
not in names. The unit test still drives Anthropic through guessing, because
there the careers page is stubbed away and the DoD's claim is what's under test.

## A board that answers is not this company's board

**The single load-bearing fact of this task.** `boards-api.greenhouse.io/v1/boards/{slug}`
(no `/jobs`) returns `{"name": "Figma", …}` — the only place Greenhouse states
*whose* board a slug is. The jobs endpoint never says.

Guessing the first word of the name is what makes this matter. Over 60 corpus
companies it found 5 boards, and it cannot tell these apart:

| guess | board says | same company? |
|---|---|---|
| `A24 Films` → `a24` | `A24` | yes |
| `Cross River Bank` → `crossriverbank` | `Cross River` | yes |
| `Prove Identity` → `prove` | `Prove` | yes |
| `DOC GPT (1-4)` → `doc` | `Marshall Wace - DOC Job Board` | **no** |
| `Brave Care` → `brave` | `Brave` | **no** (the browser) |
| `Foundry Robotics` → `foundry` | `Foundry` | **no** |
| `Starburst Labs` → `starburst` | `Starburst` | **no** |

Nothing in the response separates the top three from the bottom four. So
`states_company` requires the board name to **contain the whole company name** —
it may say more (`Automattic Careers`, `Careers at Tide`, `Razorpay Software
Private Limited`) and never less. That costs the three real companies above,
and `first-word` guessing is dropped entirely rather than kept and filtered.
Consistent with the project's existing calls: unresolved beats wrong.

## Which candidates earn their call

Measured across 260 corpus companies:

| candidate | boards found | verified |
|---|---|---|
| bare normalised name | 26 | 23 (~9% of companies) |
| `+work` `+ai` `+labs` `+jobs` `+careers` | 1 each | 1 each |
| hyphenated, `+hq` `+inc` `+io` `+team` | **0** | 0 |
| first word | 5 (per 60) | 1 |

`gleanwork` is why the suffix list exists at all — Glean is in the DoD and files
under a suffix. Cost: **5.6s per unresolved company** (6 sequential calls, and
the board endpoint is ~0.9s, not the jobs endpoint's 0.35s) → **~34 min for the
2,953-company corpus at 8 workers**, against ~6 min for the bare name alone.
Both are noise beside careers-page discovery's ~2.5 hours.

## The gate started calling Greenhouse and nobody would have noticed

Adding the guessing pass inside `resolve_all` put a live HTTP call inside two
**existing** T2.1 unit tests that stub `fetch` but had no reason to know about
`board_name`. They passed, so nothing failed — the suite just went from 0.18s to
29s and quietly acquired a dependency on Greenhouse's uptime, which VERIFICATION.md
forbids in as many words.

`tests/conftest.py` now refuses any unstubbed call at `net.get_bytes` (the one
door `get` and `fetch` both go through) and names the URL. Opt out with
`@pytest.mark.network`, which exactly one test uses and which dials 127.0.0.1:1.
**Any future task that adds a network call to a shared function inherits this
guard** — and would otherwise repeat the same silent regression.

## Still not done: data/slugs.json is still not regenerated

Fourth iteration running. The cost is now precise: careers-page ~3s/company plus
guessing ~5.6s on what it misses ≈ **2.5–3 hours at 8 workers** for 2,953
companies. Guessing alone against the corpus would resolve **~10-15%** — 3/20 on
a random sample — in ~34 minutes, which is the cheap partial refresh if one is
wanted before T6.2 automates the whole thing. `data/companies.json` is untouched
and the site still renders T1.2's snapshot.

---

# The override file — measured during T2.3 (2026-07-28)

## `board_name` cannot tell a dead slug from a Greenhouse outage; `probe` can

The obvious way to check an override is `greenhouse.board_name(slug) is None`.
It is the wrong call, and the reason is in T3.1's own docstring: `board_name`
returns None for **any** non-200, so a 404 and a 502 arrive identically. An
override checked that way fails the run whenever Greenhouse hiccups, blaming a
human for somebody else's outage — and a check that cries wolf is a check people
route around.

`greenhouse.probe` already separates them, because T3.1 needed the same
distinction for a different reason: 404 → `SLUG_UNRESOLVED`, anything else →
`PROBE_FAILED`. So verification tests `is Outcome.SLUG_UNRESOLVED` and lets every
other failure through to the build, where it is counted `probe-failed` as usual.
**Generalises:** where an outcome enum already encodes "wrong" vs "unreadable",
reuse it rather than re-deriving the distinction from a truthiness check.

## The four companies the override file exists for

Each was found by T2.2's guessing, verified against the live board, and then
**deliberately refused** because the board states a name that does not contain
the company's. Re-verified live today, all four still 200 with real roles:

| company | slug | board states | roles today |
|---|---|---|---|
| A24 Films | `a24` | `A24` | 9 |
| Cross River Bank | `crossriverbank` | `Cross River` | 28 |
| Prove Identity | `prove` | `Prove` | 11 |
| Stoke Space Technologies | `stokespacetechnologies` | `Stoke Space ` | 50 |

All four are in the corpus under exactly those names. **Razorpay was considered
and left out**: it resolves by careers-page live (measured in T2.2 above), so an
override would only pre-empt a working automatic method. An override that
duplicates automation is clutter that rots.

## Precedence is cheaper implemented as absence than as a comparison

An overridden company never enters the automatic pass at all, rather than being
resolved automatically and then overwritten. Same answer, and it skips two
careers-page fetches plus up to six board calls per overridden company — ~8.6s
each at the measured rates. Trivial at four entries; the point is that the
expensive shape is the one that looks more natural to write.

## No PyYAML: the parser is one regex, and it rejects rather than half-reads

This project still has **zero runtime dependencies**, and a flat
`<name>: <ats>/<slug>` mapping is not worth its first. The hazard of a partial
YAML parser is not that it fails — it is that it succeeds differently from what
was meant, and every such misread ends as a company quietly missing from the
site. So anything outside that one shape raises with the line number: nesting,
lists, a quoted *value*, a missing slug. A quoted *key* is accepted and stripped,
because that is the one YAML habit that would otherwise parse fine and then match
no company at all.

YAML over JSON for exactly one feature: comments. Every entry is a human
overruling measured evidence, and an override whose reason went unrecorded is one
nobody dares delete a year later. A unit test enforces that house rule — every
entry line must be preceded by a comment line.

## Still not done: data/slugs.json is still not regenerated

Fifth iteration. Unchanged from T2.2's note (~2.5–3h at 8 workers for 2,953
companies), and overrides do not move it — they add four companies to a file
nobody has rebuilt. `data/companies.json` still renders T1.2's snapshot.

---

# Company websites — measured during T1.6 (2026-07-29)

Re-run with `.venv/bin/python learning-tests/websites_live.py`.

## The corpus had no address, and that is why the site was empty

Five iterations produced sources, dedup, slug discovery, guessing, an override
file and an emitter, and a real build listed **zero** companies. Not one of those
tasks was wrong. The gap was between them: a corpus record carried `name`,
`amount`, `date` and `source_url`, and `slugs.resolve` needs a *place to look*.
It guessed `<name>.com` — so half its failures (10 of 18, measured at T1.2) never
reached a page at all, and T2.2's guessing then correctly refused to verify
boards it had no name to check against.

Every task's DoD passed. T2.1's ("resolve 7 real careers pages, rate >= 50%") was
satisfiable with hardcoded URLs while the pipeline it fed resolved nothing.
**A DoD that can be met without the thing working end to end is the failure mode
this project's acceptance criteria exist to prevent, and this one didn't.**

## Where a website can honestly be found

| source | states one? | coverage |
|---|---|---|
| YC directory | yes, `website` | **6,056 / 6,093** |
| Forbes lists | sometimes, `webSite` | 79 / 220 |
| CB Insights | not on the board — on each company's profile page | 11/12 sampled |
| FinSMEs | not in the listing — in the article | 11/12 |
| TechCrunch | not in the API payload — in the article | 5/9 |
| EDGAR | **no**, and there is no URL column of any kind | 0 |

## Two structural shapes, and nothing else is the company's site

Measured over 33 live pages, a publisher links the company it covers in exactly
two ways:

```
<a href="https://weaveos.com/">Weave</a>          the company's NAME is the text
<a href="https://anthropic.com">anthropic.com</a> the DOMAIN is its own text
```

FinSMEs and TechCrunch use the first, CB Insights the second. Both are read, name
first. **A page offering two different hosts yields None** — zero of the 33 did,
but the entire point of this field is that `slugs.py` stops guessing, and a coin
flip between two domains is the same guess wearing a source's clothes.

The publisher's own links are excluded, which matters more than it sounds: a
FinSMEs tag page is literally `<a href="finsmes.com/tag/weave">Weave</a>`, a
perfect match under the first rule.

## A website is a fact about the company, not about the round

`corpus.merge` keeps the strongest round per company and discards the rest. YC
states an address for a company whose strongest round came from EDGAR, which
states none — so the merge would have thrown away the only address in the corpus
in the act of choosing the better round. Websites are therefore collected across
*all* a company's records and reattached to the winner. Same class of bug as
T1.3's `_strength` demotion: **the merge must not lose one source's evidence
because another source's record won.**

## The lift from a real website is smaller than expected, and still decisive

30 random YC Growth companies, careers-page discovery run twice — once on the
guessed domain, once on the stated website:

```
guessed domain  5/30      real website  6/30
```

One company. That is because a YC company's name usually *is* its domain
(`triomics` → triomics.com), so the guess was already right. The number that
matters is the corpus this now runs against, where EDGAR and CB Insights names
are `Alpen High Performance Products` (thinkalpen.com) and `Mystery.org`
(mystery.org, never mysteryorg.com) — and Mystery.org is exactly the one company
in the 30 that the website resolved and the guess did not.

**So the guessed domain stays.** It resolves 5 companies the corpus would
otherwise lose, and dropping it in favour of "real websites only" would have been
a net loss dressed up as rigour.

## `no-careers-page` was two different failures wearing one name

Split, because they have different fixes and only one of them is this task's:

```
no-website        we never had an address — a corpus problem
no-careers-page   we had one and reached nothing — a retry or a JS-rendered site
no-board-link     we read their page and it named no board — T2.2's remit
```

`build-report.json` now carries the same split under `websites`, so the next
bottleneck is visible rather than inferred.

---

# Spending the websites — measured during T1.6's second half (2026-07-29)

Re-run with `.venv/bin/python -m src.slugs && .venv/bin/python -m src.build`.

## The estimate that deferred this step five times was never measured

Every iteration from T2.2 onward closed with a note saying `data/slugs.json` was
not regenerated because it costs ~2.5–3h, and each one quoted the previous one.
Nobody timed it. Timed now, on a random 64-company sample:

```
workers=16   0.96s/company
workers=48   0.28s/company
```

The full corpus ran in **~30 minutes**. The sample extrapolated to 14, so the
sample was optimistic by 2x — a random 64 under-represents the domains that hang
to the 30s timeout — but the estimate in circulation was wrong by ~6x, in the
direction that costs the most: it made a half-hour step look like a whole
iteration's budget, so five iterations in a row deferred it and shipped notes
about deferring it instead.

**An unmeasured cost estimate repeated across iterations hardens into fact.**
The loop has no memory except what gets written down, which means a number
written down once is quoted forever. Time it or don't cite it.

## Worker counts follow the target host, not the step

`resolve_all` ran one worker count for both its phases, justified by a comment
saying each thread hits a different company's domain. True of careers-page
discovery, false of guessing — which is 100% `boards-api.greenhouse.io`. Raising
the shared number to 48 would have pointed 48 threads at one host on the strength
of an argument about 48 hosts. Guessing keeps 16 (`_GUESS_WORKERS`), the same
reasoning `websites.fill` already applied for CB Insights.

## Where the 2,948 actually go

```
    88  listed
   326  no-india-roles          board read, hiring, not here
   315  probe-failed            slug VERIFIED, no probe exists  <- T3.2/T3.3
  2219  slug-unresolved
```

Resolution: 744 (25%) — 480 careers-page, 260 guess, 4 override. By ATS:
greenhouse 429, ashby 264, lever 51.

**The bottleneck moved, and the next task is not the obvious one.** Since T1.2
every note has said slug resolution is the only constraint on site size. It no
longer is. All 315 `probe-failed` companies already hold a slug a careers page or
Greenhouse itself confirmed; they are excluded solely because `build.PROBES` has
one entry. T3.2 (Ashby, 264) and T3.3 (Lever, 51) are worth up to **315 companies
against a listed count of 88** — adding a line to `PROBES` each. No slug method
can reach that: the 2,219 unresolved split 837 `no-board-link` (website read,
named no board — JS-rendered), 619 `no-careers-page` (website unreachable) and
740 `no-website` (EDGAR, which states none).

## A resolved slug is not a probeable slug

15 slugs resolved cleanly and then 404'd at probe time, landing as
`slug-unresolved` (that is why the report's 2,219 exceeds the 2,204 that
`unresolved.json` holds). Correct — a board that isn't there is not a board with
no roles — but worth knowing before reading a resolution rate as a listing
ceiling.

## Eight companies link two boards and we still refuse to choose

`ambiguous-board` fired 8 times across the corpus, and every case is a real
ambiguity rather than a parser bug: `ashby/oaknorth` vs `lever/oaknorth`,
`ashby/commure` vs `ashby/commure-athelas`, `ashby/cargado` vs `ashby/cargado.`
(a trailing period from prose). Eight companies is a rounding error against 2,219
and each one is a plausible override-file entry, which is where T2.3 put the tail.

# T1.7 — the sector filter

## No source states whether a company is software. All four were checked.

SPEC's non-goals rule out hardware, biotech and services, and the obvious
implementation — read the sector the source already publishes — does not exist.
Measured across the live corpus:

| source | in corpus | sector signal available |
|---|---|---|
| YC | 1,045 | `industry` / `subindustry` / `tags`, and unusable — see below |
| EDGAR | 985 | `Computers`, `Other Technology`, `Telecommunications`. Nothing finer exists |
| CB Insights | 683 | already filtered at the source (`cbinsights.SOFTWARE`) |
| Forbes | 163 | already filtered at the source (four software lists) |
| TechCrunch | 63 | none |
| FinSMEs | 9 | none |

## YC's subindustry categorises by market served, not by what is built

This is the finding that decided the design, and it is counter-intuitive enough
that a reasonable implementation gets it backwards. YC's taxonomy looks precise —
59 subindustry values across the corpus — and reading the non-software-sounding
buckets out would be one line. What is actually in them:

```
Consumer -> Food and Beverage    DoorDash, Instacart, Rappi, ZEPTO, Snackpass,
                                 Chowdeck ... beside Nobell Foods, Eclipse Foods
Industrials -> Automotive        Cruise, May Mobility, Embark Trucks, Zendar
Consumer -> Apparel and Cosmetics  GOAT Group, Teespring, Curtsy
```

Zepto is an Indian company hiring in India — the single most on-thesis row this
site could carry — and it is filed under Food and Beverage. Excluding that bucket
deletes exactly what the site exists to list. Only two buckets are reliably
non-software (`Healthcare -> Industrial Bio`, `Industrials -> Aviation and
Space`), and the second holds Stoke Space, which `overrides.yaml` already ships.

**So the only signal is the company's own name**, and the filter says so rather
than dressing a coarse label up as precision. Same shape as the MCA NIC-code note
in T1.7's own out-of-scope line, arrived at from the other direction.

## A name vocabulary is wrong until it is measured against the real names

Every candidate term was run against all 2,948 live corpus names before it was
kept. Four would have been shipped by anyone reasoning from the armchair, and
each one deletes real companies:

| term | looks like | actually hits |
|---|---|---|
| `labs` | a laboratory | 82 names: Cockroach, Grafana, dbt, Modal, Monad, Mysten, Ripple, Protocol, Lambda, AI21, Dapper — **dropped entirely** |
| `medical` | medical devices | Circle Medical (telehealth software) among 9 — **demoted to ambiguous** |
| `surgical` | surgical devices | Surgical Safety Technologies (OR analytics) of 2 — **demoted to ambiguous** |
| `capital` / `ventures` / `partners` | an investment vehicle | Drip Capital, Scalable Capital, Cerebro Capital, Red Ventures, Globalization Partners — all software — **dropped entirely** |

`fund` survives where `capital` does not: bounded on word boundaries it hits
`AYC Fund`, `Silicon Road Opportunity Fund I` and `SR RetailTech Fund I` and
nothing else, and it never touches `Fundbox`-shaped names.

## Non-name identifiers: demand the absence of every letter

`011235813` is a real EDGAR registrant name and T1.7 names it. The rule that
catches it has to be narrower than it first looks — the corpus also holds `0x`,
`N26`, `G2`, `R2`, `D6`, `H1`, `M1` and `01.AI`, all real software companies with
more digits than letters. "No ASCII letter at all" hits exactly two names
(`011235813`, `1910`) and zero real companies. Any rule phrased as a ratio takes
`0x` with it.

## Three verdicts, because a name is weak evidence

`software` (kept) / `ambiguous` (kept AND flagged) / `not-software` (excluded and
counted). The middle one is not indecision, it is the DoD's asymmetry made
structural: wrongly excluding a real company is invisible, wrongly including one
is visible and fixable. `robotics`, `space`, `energy`, `medical`, `surgical`,
`bio`, `devices`, `solar`, `nano` and `materials` all carry real signal that a
name cannot settle — `Gecko Robotics` sells inspection software, `Green Energy
Exchange` is a trading platform, `Fleet Device Management` is SaaS — so those
companies stay in the corpus and land in `corpus.json`'s `ambiguous` map, which
is a human-sized list rather than a 2,948-row hunt.

# T3.2 — the Ashby probe

Re-run with `.venv/bin/python learning-tests/ashby_live.py`.

## FINDINGS §1's ~151s Ashby latency is STALE. It is ~2s.

This is the single most load-bearing number the project got wrong. §1 measured a
**fixed ~151s per call, growing across runs, with 3 of 12 concurrent requests
failing**, and everything downstream was sized on it: the ~4.7h-per-1,000 refresh
budget, "Ashby weekly" versus "Greenhouse nightly" in T6.2/T6.3, and this task's
own DoD line about the 6h GitHub Actions cap. Measured today, twice, before any
code was written:

```
one call        ramp        200   2s   (1.97 MB, 120 roles)
12 concurrent   real slugs  12/12 200, 1.7s WALL  (0.1s per company)
```

The whole 264-company Ashby corpus now costs ~35s, and a full build is 5m12s end
to end — dominated by Greenhouse's 429 sequential calls, not by Ashby.

**The retries and backoff stayed anyway.** §1's throttling was real when it was
measured and read as progressive throttling of a repeat caller; it can come back,
and at 2s the guard costs nothing. What should NOT survive is the tiering
decision: **T6.3's "Ashby weekly because it is 151s/company" no longer has a
premise.** Re-measure before building that workflow rather than inheriting the
number.

## A wrong Ashby slug 404s. Ashby is not Lever's trap.

Measured against a deliberately unregisterable slug: `404`, body `Not Found` as
plain text rather than JSON. So an empty `jobs` array from a 200 is an honest
"no open roles" and can be believed, exactly as on Greenhouse. Only Lever (T3.3)
needs `empty-board-unverified`.

## There is no `meta.total`. Truncation is undetectable.

The response is `{"jobs": [...], "apiVersion": "1"}` and nothing else, so
Greenhouse's agreement check — the thing that makes a short board *detectable* —
has no counterpart here. All the probe can refuse is a body that isn't whole
JSON, which is why a malformed 200 is RETRIED rather than recorded: a truncated
transfer is transient in exactly the way a 503 is, and the status line cannot
tell them apart.

Also absent: any way to decline the job descriptions. Greenhouse has
`content=false`; Ashby ships `descriptionHtml` *and* `descriptionPlain` inline,
which is why one 120-role board is 1.97 MB.

## One role can be in several places, so India roles are counted by ROLE

`secondaryLocations` sits beside the flat `location` string — 158 of them across
Ramp's 120 roles — and each entry is an object wrapping its own `location`
string, not a bare string. Reading only the primary undercounts multi-location
postings (§2 predicted this); counting the *strings* over-counts them, because
one posting open in Bengaluru and Mumbai is one job in two cities.

That is what forced `build.Provider`: the probe and the location-unwrap travel
together per ATS, because Greenhouse nests exactly one `location.name` and Ashby
gives a list. `india.is_india` stays a function of a string, as its own docstring
argued it should.

## Where the 2,915 go now

```
   110  listed                  was 88
   558  no-india-roles          was 326  (+232 Ashby boards read, hiring, not here)
    51  probe-failed            was 315  -- exactly T3.3's Lever share, nothing else
  2196  slug-unresolved
```

Of the 264 Ashby companies: 22 listed, 232 no-india-roles, 10 `slug-unresolved`
(the slug resolved cleanly at T2.1 time and 404s now — the same "a resolved slug
is not a probeable slug" effect T1.6 measured on Greenhouse).

**T3.3 (Lever, 51 companies) is now the entire remaining probe gap**, and after
it `probe-failed` should be 0. The 2,196 `slug-unresolved` are the next real
frontier, and they are a slug problem, not a probe one.

## Spot-checked, because "matched India" is the claim that can quietly be wrong

`ashby/cursor` → 2 of 122 roles, both literally located `India` with no city, so
the row carries `cities: []` — the "India without naming where" case T3.4 wrote
that field for. `ashby/ambient.ai` → 5 of 15, all `Bengaluru` with no `, India`
suffix, caught by the city list rather than by the country name.

---

# T3.3 — the Lever probe (2026-07-29)

## The documented trap does not reproduce. A wrong Lever slug 404s.

§1 recorded that a wrong slug "can return HTTP 200 with an empty array", and
that single sentence is why `empty-board-unverified` exists in the outcome
vocabulary at all. Re-read the row it came from: **5 slugs tried, 3 404'd, and
the 2 that returned 200 returned zero postings.** The 200-empty pair were never
shown to be *wrong* slugs — the inference was that they might be, and that we
could not tell. That was the honest reading then and it is still the honest
reading now.

Ten wrong slugs of three deliberately different shapes, measured today:

| shape | examples | answer |
|---|---|---|
| nonsense | `no-such-company-india-radar-xyz`, `zzzz-not-a-board-99` | 404 |
| near-miss spelling | `matillon`, `mindtickle-inc`, `tala-mobile` | 404 |
| our own slug minus its suffix | `asapp` (we hold `asapp-2`), `easypost`, `oleria` | 404 |

All ten: `404`, body `{"ok":false,"error":"Document not found"}`. Dropping
`?mode=json` changes nothing — the parameter is the format, not the door. So the
**mechanism** is narrower than it was written down as: nothing constructible
answers 200-with-empty-array.

## The outcome earns its place anyway, and three live companies are why

`ramenvr`, `tesorio` and `trela` — all three in our own corpus, all three
resolved by careers-page — answer **200 with `[]`** right now. An abandoned
board, a renamed company and a firm that genuinely isn't hiring produce that
byte for byte, and unlike Greenhouse there is no `boards/{slug}` name lookup to
ask a second question of. So an empty Lever board stays `empty-board-unverified`:
excluded, and counted as an absence of knowledge rather than as a finding.

This is the one place the three probes deliberately disagree. Ashby's empty array
is believed (§"A wrong Ashby slug 404s") and Lever's is not, even though both
providers 404 a wrong slug. The difference is not the 404 — it is that Ashby was
checked against a board we could name and Lever cannot be. Keeping the stricter
rule costs 3 companies out of 51, all of which would have been excluded from the
site either way; what it buys is that T5.3's integrity footer counts them under
"could not check" instead of claiming we did.

**The DoD's integration check is therefore unsatisfiable as written** — "probe a
known-bad slug, assert outcome is `empty-board-unverified`" now yields
`slug-unresolved`, correctly. `learning-tests/lever_live.py` §5 asserts what the
check is *for*, against boards that really do answer 200-empty today, and pins
the 404 case beside it. **Flagged for the human rather than quietly reworded.**

## The response is a bare array, and `allLocations` is the whole location answer

No envelope, no `meta.total` — the JSON array *is* the body, so truncation is
undetectable here exactly as on Ashby. `categories.allLocations` sits beside the
primary `categories.location` and, across 158 postings on six boards, is present
on all 158 and **contains the primary in every case where a primary exists**. So
it is used whole rather than prepended to, unlike Ashby's `secondaryLocations`
which is genuinely the *other* places. Prepending would double every city on
every row — invisible in the role count, visible in the site's city filter.

The one exception found: a Kpler posting states `location: null` with
`allLocations: []`. A role with nowhere stated, not a crash.

## Cost, and where probe-failed went

51 slugs in **15.1s** wall at 12 workers; individual calls 2–5.4s; every one
answered first try, no 5xx and no throttling. So no retry loop and no batch
wrapper — the same shape as `greenhouse.probe`, which carries 429 companies to
this one's 51. The full sequential build went **5m12s → 9m38s**, against a 6h
cap. `ashby.probe_all` is the upgrade path if that stops being true.

```
   116  listed                  was 110
   595  no-india-roles          was 558
     3  empty-board-unverified  was 0
     0  probe-failed            was 51   <- the probe gap is closed
  2201  slug-unresolved         was 2196
```

The 51 Lever companies split 6 listed / 37 no-india-roles / 5 slug-unresolved
(404 today, resolved cleanly at T2.1 time — "a resolved slug is not a probeable
slug", now seen on all three providers) / 3 empty-board-unverified.

**`probe-failed` is 0 for the first time, and that is the point.** It no longer
means "we hold a slug nothing can read"; it means only what the vocabulary says
it means — we tried and failed. Every remaining exclusion is a slug problem:
**2,201 `slug-unresolved`, of which 1,251 have a website we already hold.** That
is the whole of the next frontier, and it is E2's, not E3's.

## Spot-checked, because "matched India" is the claim that can quietly be wrong

`lever/mindtickle` → 19 of 21 postings in India (Bengaluru and Pune; MindTickle
is India-headquartered, so a high ratio is right and a low one would have meant
the `allLocations` unwrap was wrong). `lever/moonpay` → 1 of 15, located
`Remote - India` with no city, so the row carries `cities: []`. `lever/nium` → 13
across four cities including Surat, which no other listing on this site reaches.

---

# Roles, apply links and the remote flag — measured during T4.1 (2026-07-29)

`learning-tests/roles_live.py`, over the 116 companies the site lists today.

## Every role states a title and a URL, and all 10 sampled apply URLs are 200

1,112 India roles across all three providers: **1,112 carry a string title and a
string URL**, no nulls, no missing keys. So the per-provider difference is a
*spelling*, not a shape, and it lives in `build.PROBES` as three field names
rather than as three functions:

| provider | title | posting URL | apply-form URL | workplace |
|---|---|---|---|---|
| greenhouse | `title` | `absolute_url` | — | *never states one* |
| ashby | `title` | `jobUrl` | `applyUrl` | `workplaceType` |
| lever | `text` | `hostedUrl` | `applyUrl` | `workplaceType` |

The **posting page** is what ships, not the deep link to the form: Greenhouse has
no counterpart to `applyUrl`, and the posting carries the apply button anyway.
T4.1's DoD check — 10 listed companies spread across all three providers, one
India role each — returned **10/10 HTTP 200**. Two of them are worth noting:
Airbnb's `absolute_url` is `careers.airbnb.com`, not a greenhouse.io domain (a
board can be white-labelled onto the company's own host), and 6Sense's is
`boards.greenhouse.io` where the site's own board link builds
`job-boards.greenhouse.io`. Both resolve; a check that pattern-matched the host
instead of fetching it would have failed on live data that is fine.

## Ashby says `OnSite`, Lever says `onsite`, Greenhouse says nothing at all

Measured over the same 1,112 India roles:

```
ashby       135 roles   workplaceType: OnSite 91, Hybrid 21, Remote 11, absent 12
lever        38 roles   workplaceType: hybrid 20, onsite 18
greenhouse  939 roles   workplaceType: ABSENT ON ALL 939
```

Two vocabularies that differ only in casing, so `.lower()` merges them and
`india.WORKPLACES` is the same three words. **Greenhouse states this nowhere** —
not on the role, not in `metadata` (null on Komodo Health and YugaByte; on Scale
AI it holds `Domain` and `External Department` and nothing about workplace), and
the description is dropped by `content=false` anyway. Since Greenhouse is 84% of
the India roles, a location-string rule has to carry it, and `workplace` is
`None` far more often than not. **That absence stays an absence**: defaulting it
to `onsite` would invent the most common answer for the largest provider.

Where a board states a workplace it is believed over the string, because it is
the field that exists to answer the question. The two disagree on **2 of 173**
roles that have both: a role located `India - Remote` that states `OnSite`, and
one located `India Office` that states `hybrid`. That is a company contradicting
itself, not a rule to pick.

## The DoD's "a city OR an explicit remote flag" does not hold on live data

Of the 116 listed companies, **28 name no India city at all**. With both routes
in — the board's own `workplaceType` and the location string — 13 of those state
remote and **15 state nothing at all**: a board that says literally `India`.

```
27  'Remote - India'      -> remote
 7  'India'               -> nothing stated
 4  'India (Remote)'      -> remote
 2  'Remote, India'       -> remote
 2  'India Remote'        -> remote
 1  'India, Remote'       -> remote
 1  'Remote - Anywhere, Remote - India'  -> remote
 (and, with a city AND a remote claim: 2x 'Remote - Bangalore, India')
```

Komodo Health, Scale AI, Starburst, Tamara, Temporal and YugaByte are the shape
of it: Greenhouse boards, location `India`, no `workplaceType`, no metadata, no
second question to ask. **There is no honest way to give those companies a city
or a remote flag.** The third clause of the same acceptance — "no company
displays an empty location" — is satisfiable and is what protects the reader, so
the site renders the three cases apart: cities where named, `Remote — India`
where the board says remote, and otherwise **what the board literally said**.
Flagged for the human rather than quietly reworded; see TASKS.md T4.1.

`role_errors` enforces the deterministic half: a role's `locations` list must be
non-empty. A role became an India role by naming a place in India, so a role with
nothing to render a location from is a contradiction rather than a gap.

## `In-Office` answers the workplace question it refuses the India one

T3.4 deleted the `IN-` prefix rule because it matched `In-Office` and produced 47
false-positive *India* roles. Asked instead how a role is worked, `In-Office` is
a perfectly good answer — the same string, read for a different fact, and only
one of the two readings is a claim about where the job is. Both rules now live in
`src/india.py` beside each other and `test_in_office_answers_the_workplace_...`
pins the distinction so a future reader doesn't "fix" one into the other.

`hybrid` is matched before `remote` and `onsite`: `Hybrid; In-Office` states two
things and the more specific one is the answer.

## The published shape, and where the 1,112 roles land

```
116 companies, 1,112 India roles, 0 with an empty location list
workplace:  822 not stated · 117 onsite · 107 remote · 66 hybrid
cities:      88 companies name at least one · 28 name none
             of those 28: 13 state remote · 15 state nothing but "India"
```

Outcomes are unchanged by this task (116 listed, 595 no-india-roles, 2,201
slug-unresolved, 3 empty-board-unverified, 0 probe-failed) — enrichment must not
move the listed set, and it didn't.

## The e2e was validating a CACHED COPY of the page under test

Worth more than the feature it was found by. `make check` went green on an
`index.html` from **before the edit under test**: the page reported "This page
reads schema v3" while the file on disk said 4, and *every behavioural check
still passed against it*, because the stale page and the stale data agreed with
each other.

The mechanism: `scripts/e2e.sh` serves on a fixed port, so the document URL is
byte-identical every run; `python -m http.server` sends no `Cache-Control`, so
the browser assigns a heuristic freshness lifetime and re-serves the copy it
already has. Proven by loading the same file on a fresh port — identical bytes,
correct result. The page's own `fetch(src, {cache: 'no-cache'})` fixes the JSON
and cannot fix the document that fetches it; **FINDINGS T1.2 is the same trap one
level down**, and fixing it there is what hid it here.

`open_page` now appends a per-run token to every URL. The failure mode this
closes is the dangerous kind: not a red gate, a *green* one that proves nothing
about the code just written.

## Four mutations, and the one that got away

Confirmed biting: unlinking the role titles, a remote filter that ignores
`workplace`, and a placeless company rendering a blank location.

The fourth passed a full green gate and had to have a check written for it —
**defaulting an unstated workplace to `on-site` in the badge**. 822 of 1,112
roles state nothing, so that mutation invents the most common answer for the
largest provider and prints it as though the company had said it. It is the
ambiguous zero wearing a badge, and nothing in the suite objected until
`a role whose board stated no workplace shows no badge` existed.

---

# Salary benchmark — measured during T4.2 (2026-07-29)

## AmbitionBox publishes the figure, the sample AND its own recompute date

`https://www.ambitionbox.com/salaries/<hyphenated-name>-salaries` is
server-rendered Next.js, so the numbers are in the hydration payload as JSON
rather than in formatted markup a redesign moves:

```
props.pageProps.salaryData.data = {
  "totalSalaryAverage":   "21.2",                    # lakhs per annum, India CTC
  "totalSalaryDataPoints": "7060",                   # self-reported salaries behind it
  "lastUpdated":          "2026-07-28 08:26:01.0",   # when the SOURCE recomputed it
}
props.pageProps.companyHeaderData.companyName = "Razorpay"   # whose page this is
```

`lastUpdated` is why this feature is publishable at all. Across the 82 companies
that carry a figure, it ranges from **today back to 2025-10-12** — so "₹21.2L"
without its date is a nine-month-old sample presented as a statement about now.
SPEC feature 8 asks for the date; the data turns out to insist on it.

## Coverage: 82 of 115 listed, and the 33 absences are three different things

| outcome | n | what it is |
|---|---|---|
| figure | 82 | published |
| 404 | ~46 of a 116-company sweep | no page: nobody has reported a salary there |
| 200, all fields null | 5 | page exists, company matches, no figure yet |

All three are absences and none is an error. A single pass found **65 of 116**;
the same work with backoff found **82 of 115**. The difference is entirely the
rate limit below.

## The rate limit counts requests over a window, and going slower does not help

Measured in this order, all against the same 116-company listed set:

| run | workers | result |
|---|---|---|
| 1 (30 companies) | 8 | clean |
| 2 (116) | 8 | clean, 65 figures |
| 3 (116) | 8 | **86 of 116 blocked** |
| 4 (116) | 8 | **116 of 116 blocked** |
| single call, seconds later | 1 | 200, full page |
| 5 (32) | 4 | clean |
| 6 (32) | 2 | clean |
| 7 (32) | 1 | **19 of 32 blocked** |

Run 7 is the one that settles it: one worker was the *worst* result, because by
then it was the third sweep inside a minute. It is cumulative request volume
over a rolling window, not concurrency, so lowering the worker count is not the
fix and backoff is. A rested burst at 8 workers is clean.

**The block is a 403 and a genuine absence is a 404.** That distinction is the
whole recovery: retrying the 404s would triple the run to re-learn that 46
companies still aren't listed, and not retrying the 403s empties the feature.
Same shape as Ashby's 404-is-final rule in T3.2, for a different reason.

## A wrong slug 404s, so the identity risk is narrow — but it is not zero

Nonsense slugs and real-but-unlisted companies (Anthropic, Anyscale, Deepgram)
all 404 cleanly. What remains is a *different real company* sharing a normalised
name, and `slugs.states_company` is the same rule T2.2 measured on job boards,
reused unchanged.

**The loose direction of that rule is load-bearing here, which was not obvious.**
Two of the 82 pages state a name LONGER than the corpus name — `Kaseya` →
`Kaseya Software`, `Tide` → `Tide - Business Management Platform` — so an
exact-match rule would silently drop them. Zero name mismatches were observed
across the listed set.

## Build cost: 5m12s -> 10m41s, and the enrichment is now the slow half

The full build with the enrichment in is **10m41s**, against ~5m before. The
added time is almost entirely backoff waiting out 403s, not fetching. Still far
inside any workflow cap, but **T6.2/T6.3 should tier on this number rather than
on the probe latencies alone** — the slowest thing in a build is no longer an
ATS.

---

# MCA snapshot — measured during T4.3 (2026-07-29)

## The whole enrichment universe is three calls and 18 seconds

`filters[CompanySubCategory]=subsidiary of company incorporated outside India`
at `limit=10000` returns **24,102 records in 3 calls, 17.9s**, exact — the count
FINDINGS predicted, unchanged. Every record carried all five kept fields:
**zero blank CINs, names, dates, addresses or statuses across 24,102 rows.**

**The "502 after ~20 calls" constraint is real and this pull never reaches it.**
It shaped the design anyway — the cost of a wrong assumption here is a nightly
build that goes down when someone else's Elasticsearch does — but the pull
itself is nowhere near the wall. Two full pulls minutes apart both ran clean.

**The dataset is more current than FINDINGS recorded.** Newest incorporation in
the slice is **2026-06-01**, not the 2026-03-31 measured in July's sample. The
37 state-wise datasets are still frozen at 2021-03-31; nothing about that
changed, and the gap between the two is now five years and three months.

**The wrong filter spelling still returns `total=0` today**, pinned beside the
right one in `learning-tests/mca_live.py` §2. That is why `pull` refuses an
answer under 90% of the *expected* 24,102 and not merely under the API's own
reported total: when the filter stops matching, the API's total agrees with the
empty answer, so only the measured figure catches it.

## The foreign-subsidiary filter excludes Indian-origin companies BY CONSTRUCTION

This is T4.4's real ceiling and it is not a matching problem.
`STRIPE INDIA PRIVATE LIMITED` is in the slice; **`RAZORPAY SOFTWARE PRIVATE
LIMITED` is not, and no amount of name matching will find it** — Razorpay is an
Indian company, so it is not a subsidiary of one incorporated outside India. The
same holds for every India-founded company the corpus carries.

Measured with a crude three-suffix name join against `data/companies.json`:
**32 of 115 listed companies hit the table.** That is T4.4's approximate ceiling
on this slice. Lifting it means pulling the unfiltered 3.67M-row table (367
calls, and the 502 wall becomes a real constraint rather than a theoretical one)
— which buys Indian-origin companies a badge, and is a decision about what the
badge *means*, not an optimisation. A badge that only foreign subsidiaries can
earn will read on the site as a mark against Indian startups unless T5.3 says
what it is.

## The registered address is comma-separated, city fourth from the right

    201 Creative Industrial Estate 12 N M Joshi Marg,Mumbai,Mumbai City,Maharashtra,400018-India
                                                     ^city ^district      ^state    ^pin-country

SPEC feature 9 wants a registered city, and that is `rsplit(",")[-4]` — on the
rows inspected. It is **not** validated over all 24,102, so T4.4 owns proving it.
The snapshot keeps the address WHOLE for exactly that reason: a lossy trim here
would cost a re-pull against the flaky API to undo.

---

# MCA name matching — measured during T4.4 (2026-07-29)

## The word boundary is the entire difference between a match and a wrong CIN

A registered name is the company's name followed by the register's own words, so
the join looks like a prefix test — and a *character* prefix test is wrong on
live data in both directions. Measured against all 24,102 registered names:

| corpus name | character prefix finds | what it is |
|---|---|---|
| `Kong` | `KONGSBERG MARITIME INDIA` | a Norwegian maritime group |
| `Notion` | `NOTIONEXT INDIA` | somebody else |
| `Stripe` | `STRIPES ACADEMY LEARNING AND DEVELOPMENT INDIA` | somebody else |
| `Scale` | `SCALEFFICIENT`, `SCALEFLUIDLY`, `SCALEUP STREET`, `SCALETRON` | four of them |

So the match cuts only between words. But the words have to be run together to
compare, because the register JOINS names the corpus spaces: `AMBIENTAI INDIA`
is `Ambient.ai`. Running them together re-opens the trap from the other side —
`HIGH TOUCH HEALTH SOLUTIONS GLOBAL` concatenates to `hightouch...`, and that is
a healthcare company, not the data one.

**The rule that survives both: the register may JOIN the company's words but
never SPLIT one.** A candidate is kept only if the words of the registered name
it consumed number no more than the company's own words. `Ambient.ai` spends two
words and consumes one; `Hightouch` spends one and would need two, so it is
refused. That single comparison is what all five false positives above die on.

The other direction is `slugs.states_company`'s rule unchanged — the register may
say MORE and never less. `COCKROACH INDIA` for `Cockroach Labs` is refused for
the same reason `greenhouse/brave` is refused for `Brave Care`.

## Two tiers, because "says more" is right and wrong in the same shape

Of the 116 listed companies, 32 reach a registered name that is theirs plus at
most `INDIA` and a legal form. Another 30 reach one that says more — and that
set contains both `GLEAN SEARCH TECHNOLOGIES INDIA` (Glean) and `FERN & ADE
INDIA` (not Fern). Nothing in the register tells those apart, so the tier is
published nowhere and reported in `build-report.json` under `mca.held` for a
human. Unresolved beats wrong, as everywhere else here.

**Zero ambiguity at the publishing tier, measured over the whole corpus**: all
2,915 corpus names against all 24,102 registered names produce 92 `exact`
matches and **not one** name reaching two different CINs. The guard still ships,
because `Scale` reaching both `SCALE AI INDIA` and `SCALE FACILITATION PARTNERS
INDIA` is a live one-word-away miss — and the corpus holds `Scale AI` as its own
company.

## The registered city is the district field, NOT the locality — correcting T4.3

T4.3 read `rsplit(",")[-4]` off one Mumbai row where the locality and the
district both said `Mumbai`, and flagged it unvalidated. Validated now over all
24,102:

| field | blank | distinct | what it holds |
|---|---|---|---|
| `[-4]` locality | 252 | 2,271 | `Kandivali West` (EBANX), `Shaikpet` (Workato), `Sector -45`, `NH-8` — 349 street fragments |
| `[-3]` district | **0** | 476 | `Bangalore`, `Pune`, `Hyderabad`, `South West Delhi` |
| `[-2]` state | 0 | 29 | clean |

The locality is a neighbourhood; the district is the city a person would name.
Case is the register's own noise — `NEW DELHI` (680) sits beside `New Delhi`
(1,894) for one place — so it is evened out and nothing else is.

## A CIN has a shape, and all 24,102 keep it

`[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}` matches every row in the snapshot, so
`build.mca_errors` refuses one that doesn't: this is the one enrichment whose
mistake is a public claim about another company's legal identity, and a CIN that
isn't a CIN means the parse went wrong rather than that the company is unusual.

## An Indian-origin company CAN be in the slice — partly correcting T4.3

T4.3 concluded that `RAZORPAY SOFTWARE PRIVATE LIMITED` cannot be a foreign
subsidiary and no name matching would find it. True of that entity — but
**`RAZORPAY TECHNOLOGIES PRIVATE LIMITED` is in the slice**, because Razorpay's
holding company is incorporated outside India. The ceiling T4.3 described is
real and slightly higher than it said: the filter excludes companies whose
*parent* is Indian, not companies that feel Indian. It is still a filter about
corporate structure, which is why the site's footer now says so — a badge no
India-founded company can earn reads as a verdict on them unless the page states
what it is.

---

# The integrity footer — measured during T5.3 (2026-07-29)

## The site cannot count this, and that is the whole reason the field exists

`companies.json` holds 116 rows. The honest footer says **711 of 2,915 checked,
2,204 not** — three numbers, none of which is derivable from the file's own rows.
A renderer counting what it has can only ever produce "116 of 116", which is the
one sentence this project's premise forbids: a claim of completeness the data
cannot back.

So schema **v7** adds an `integrity` block (`corpus_size`, `checked`,
`unchecked`) copied out of the build report rather than recomputed. Copied, not
re-derived, because a second count of the same thing is a second chance to
disagree with the first — and the two files are then two artifacts of one build
that can be asserted against each other.

`checked` is `outcomes.CHECKED` — listed **or** `no-india-roles`. A company we
read and found nothing on was checked; that is a finding. The other 2,204 are
absences of knowledge and the footer says so.

## The failure this can actually have is the two files drifting apart

On the real path the sum can only hold: `report()` computes `unchecked` as a
subtraction, so validating it there proves nothing. The check earns its place
one level up — `integrity_errors` refuses counts that do not account for the
corpus, and refuses `checked` below the number of rows being written, which is
the deterministic form of "this footer is describing a different build than
these rows". The e2e then asserts the rendered sentence against
`build-report.json`, the OTHER file.

The hand-written e2e fixture is the case that exercises the schema half, so it
carries 9 checked of 30 rather than a full-coverage block: a fixture where
everything was checked would render the one sentence the footer exists to avoid.

## Three mutations, all of which bite

- `write` stops validating the counts → `test_a_footer_that_does_not_add_up_...` red.
- the site counts its own rows → e2e: `expected [711 2915 2204] got [116 116 0]`.
- the footer is filled *before* the schema-version guard → a dataset the page
  refuses to render still gets a coverage figure printed under the refusal. This
  is the one that needed care: the first attempt at it left `n` undefined, so
  `load()` threw, the fetch `.catch` swallowed it, and the check went green for
  a reason that had nothing to do with the mutation. **A mutation that makes the
  page fail EARLIER can pass a check it was written to break.**

## Rebuild cost, re-measured: 10m59s

Against T4.2's 10m41s, on a corpus of 2,915 with the same outcomes (116 listed,
0 probe-failed, 3 empty-board-unverified). `build-report.json` regenerated
byte-identical, which is the useful part: the pipeline is reproducible across a
day, so **T6.2/T6.3 can diff snapshots for real change rather than churn.**

A schema bump now costs a full live rebuild, because the page refuses the
published file the moment `SCHEMA_VERSION` moves. That is the correct failure —
it is the stale-data trap from T1.2 caught by design instead of by luck — but it
means **a schema change is an ~11-minute task, not a one-line one.**

---

# The nightly workflow — measured during T6.2 (2026-07-29)

## Greenhouse is no longer 0.35s. It is 1.2s, and it is now the slow provider.

Re-measured over 25 random live slugs from the real corpus: **1.20s each**,
against FINDINGS §1's 0.35s median. At 429 slugs sequentially that is ~8.6
minutes — and it is the largest single line in the build.

Full build, wall, end to end: **11m26s** (`time .venv/bin/python -m src.build`,
logs/t62-full-run.txt), at **3% CPU**. This job is network wait, not compute, so
a bigger runner buys nothing and concurrency is the only lever that would.

```
Greenhouse  429 slugs, sequential, 1.2s      ~8.6 min
Ashby       264 slugs, concurrent            ~35s    (T3.2's re-measure, held)
Lever        51 slugs, sequential            ~1 min
salary      116 listed rows, with backoff    ~1 min
                                             --------
                                              11m26s = 3% of GitHub's 6h cap
```

## So the Greenhouse/Ashby tiering has no cost left to justify it

FINDINGS §1 sized the whole refresh budget on Ashby at ~151s/company — eleven
hours for this corpus — and that is the entire reason T6.2/T6.3 were split into a
nightly tier and a weekly one. Ashby now answers in ~2s. The ordering has
inverted: **the expensive provider is Greenhouse, and it is 8.6 minutes.**

A split would now mean republishing one provider's rows from yesterday's file
while stamping today's snapshot date on them. That is the same class of lie as
rendering an unchecked company as "not hiring". One nightly, everything fresh.

## Two runs three hours apart: the spine is byte-stable, the enrichment is not

116 rows both times, and **zero non-salary differences between any pair of rows**
— which is what makes a nightly diff readable as real hiring movement rather than
scrape noise, and what T7.1 will depend on.

All 116 changed lines were `salary`: **11 figures lost, 11 gained, 1 changed.**
That is AmbitionBox's rolling request window (§T4.2) sampling differently, not
companies changing what they pay. Consequences worth knowing before T6.4:

- **The "no change, no commit" path will essentially never fire.** Salary churns
  every run, so every night commits.
- **A throttled night publishes a coverage regression**, because the enrichment
  overwrites a real figure with `null` rather than keeping the last known one.
  Nothing here is wrong — a null is an honest absence and the build cannot tell a
  403 from a company nobody has reported — but the *site* oscillates between 82
  and 71 salaries for no real-world reason. Making enrichment sticky (never
  replace a figure with an absence) is the obvious fix and belongs to whoever
  takes T6.4, not to the workflow.

One figure's `observed` date moved **backwards**, 2026-07-29 to 2026-07-27
(Celonis). It is AmbitionBox's own recompute field and the row links its source,
so it is reported, not invented — but do not assume that date is monotonic.

## `timeout` is the bound, and it is a hard dependency

`scripts/nightly.sh` wraps the build in coreutils `timeout` rather than trusting
GitHub's 6h job cap, so a hand run is bounded too and the dry-run test can prove
the bound bites (exit 124, nothing committed) instead of hoping. `timeout` ships
on ubuntu-latest and came from homebrew here; a bare macOS without coreutils has
no `timeout` and the script will fail loudly on the first line rather than run
unbounded, which is the right failure.

---

# The weekly tier that should not exist — measured during T6.3 (2026-07-29)

## Ashby is 9% of the probe time. The tier it was named for buys 37 seconds.

T6.3's entire DoD is "tiering is by measured cost — re-measured, not inherited",
so the measurement is the deliverable and the workflow is what it ruled out.
Measured against the live 744-slug corpus (`learning-tests/nightly_tiers_live.py`,
logs/t63-tiers.txt):

```
ashby       261 slugs, WHOLE corpus, concurrent      36.9s     9%
greenhouse  422 slugs, 0.54s/call sequential          3.8 min  56%
lever        51 slugs, 2.81s/call sequential          2.4 min  35%
                                                     --------
all three probes                                      6.8 min
```

A weekly Ashby tier saves **37 seconds a night** and pays for it with six days of
staleness on 261 companies — republished under a snapshot date claiming today.
That is the same class of untruth as rendering an unchecked company as "not
hiring", for a saving of 0.5% of the nightly. Not built.

## The per-provider ordering has now inverted TWICE, and each time on real data

FINDINGS §1: Ashby ~151s/call, the most expensive thing in the project, and the
reason the nightly/weekly split was designed at all. T3.2: Ashby ~2s. T6.2:
Greenhouse 1.2s/call and the new slow provider. Today: **Greenhouse 0.54s and
Lever 2.81s** — Lever is now the per-call slowest by five times, and its 51 slugs
cost within striking distance of Greenhouse's 422.

Nothing in this repo changed between T6.2's measurement and this one; they are
hours apart. So these are not stable numbers to design around, and the lesson
generalises past tiering: **a schedule derived from a provider's latency is a
schedule derived from someone else's weather.** The build fits in 3% of the job
cap by an 8x margin. Spending that margin to avoid re-measuring is the trade
worth making.

Corollary for T6.4 and anyone tempted to parallelise: the obvious target is no
longer Greenhouse. Lever at 2.81s x 51 sequential is 35% of probe time for 7% of
the slugs. Measure before optimising — twice now, the answer was not the one
everyone was quoting at each other.

## The decision is pinned by tests, because a decision not to build has no diff

Two checks in `tests/test_nightly.py`, both mutation-verified:

- `test_the_nightly_probes_every_resolved_provider` — every ATS in `slugs.json`
  has a probe in `build.PROBES`. Dropping Ashby from `PROBES` (a weekly tier in
  its crudest form) turns it red. It also catches the unrelated case where T2.x
  resolves a fourth ATS nothing can read.
- `test_one_schedule_because_a_second_would_be_a_slower_tier` — exactly one
  workflow carries a `schedule:`. Adding `weekly.yml` turns it red.

The glob is `*.y*ml`: GitHub reads both spellings and a `weekly.yaml` would
otherwise walk past the check.
