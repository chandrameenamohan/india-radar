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
