# SPEC — INDIA·RADAR

*(working title, placeholder — rename before launch)*

## Thesis

**Funded software companies that are hiring in India right now, proven by their own job board — not by a claim.**

## What it is

A static site: one `data/companies.json`, vanilla JS, no backend, no database,
published on GitHub Pages. Every company on it is (a) a software company that has
raised roughly Series A or more, and (b) showing at least one open India role on
its own ATS at build time. HQ may be anywhere — US, UK, Canada, Europe, Asia,
Australia.

The build is **stateless**. Each run recomputes the whole site from live sources.
There is no history store, no incremental state, no migrations. A company that
stops hiring in India simply stops appearing.

## Architecture in one line

```
funding corpus  ->  resolve ATS slug  ->  probe board  ->  keep India roles
                ->  enrich (roles/city/salary/MCA)  ->  emit companies.json
```

Enrichment hangs off the job-posting spine. Any enrichment may fail, degrade, or
arrive late without taking the site down.

---

## Features

Each carries an **observable acceptance**: what a user or caller can see when it works.

### 1. Funding corpus assembly
Scrape four free sources into a deduplicated company list with name, funding
amount, date, round letter (when stated), and source URL.
Sources: FinSMEs, YC company directory, SEC Form D (EDGAR), TechCrunch/Forbes/CBI lists.

**Acceptance:** `corpus.json` exists with ≥1,000 distinct companies; every record
carries a source URL that resolves; running the build twice produces the same
company set (dedup is deterministic, not order-dependent).

### 2. "Series A or more" filter — amount-based proxy
Qualify a company when a stated round letter is A or later, **or**, when no
letter is given, when a disclosed round is ≥ $5M. Record which rule fired.

**Acceptance:** every corpus record has `qualified_by` set to exactly one of
`letter` or `amount`; a record with neither a letter nor an amount is excluded and
counted in the build report, never silently dropped.

### 3. ATS slug resolution
For each company, find its job-board slug by (a) regexing its careers page for
board URLs, then (b) guessing the slug from the company name and probing
Greenhouse directly, then (c) consulting a hand-maintained override file.

**Acceptance:** `slugs.json` maps company → `{ats, slug, method}` where method is
one of `careers-page | guess | override`; unresolved companies land in
`unresolved.json` with a reason, and the build report prints the resolution rate.
Measured baseline to beat: ~50% from (a) and (b) alone.

### 4. Board probe
Fetch open roles per company from Greenhouse, Lever, or Ashby.

**Acceptance:** for a known-good slug the probe returns the same role count the
provider's own public board shows. For Greenhouse specifically, the returned count
equals `meta.total` in the same response.

### 5. India role filter
Keep a company when ≥1 open role matches India by city-name list. Handles
`Bengaluru, India`, `Remote - India`, `India - Remote`, `IN-Pune`, multi-city
strings like `Bengaluru, India; Mumbai, India`, and Ashby's `secondaryLocations`.

**Acceptance:** a fixture file of real location strings (including the known
false-positive traps `In-Office` and `Hybrid; In-Office`) classifies with zero
false positives and zero false negatives.

### 6. Enrichment — India roles and apply links
Attach each matching role's title and direct apply URL.

**Acceptance:** every listed company has ≥1 role with a URL that returns HTTP 200
and lands on that company's posting.

### 7. Enrichment — city and remote flag
Parse India cities and remote/hybrid/onsite from the same location strings.

**Acceptance:** each company shows ≥1 India city or is explicitly flagged remote;
no company displays an empty location.

### 8. Enrichment — salary benchmark
Attach an AmbitionBox-style India CTC figure with its source URL and observation date.

**Acceptance:** where present, the figure renders with its date and a working
source link; where absent, the row renders cleanly without it. Absence is never
an error.

### 9. Enrichment — MCA verification badge
Attach CIN, incorporation year, registered city and entity status from the
**RoC-wise Company Master Data** dataset
(`4dbe5667-7b6b-41d7-82af-211562424d9a`).

**Acceptance:** a matched company displays a CIN that resolves on the MCA portal;
match confidence is recorded and anything below threshold is held for manual review
rather than published. Unmatched companies render normally without a badge.

> **UNBLOCKED** (2026-07-28). Registered key obtained; all three unknowns resolved.
>
> - Page size **10,000** → the full 3,674,314-row table is **367 calls**.
> - The foreign-subsidiary filter value is
>   `CompanySubCategory = "subsidiary of company incorporated outside India"`
>   → **24,102 companies**. (My earlier guess "Subsidiary of Foreign Company"
>   does not exist, which is why it returned 0.)
> - `CompanyStateCode` is optional; a flat scan works.
>
> **Never use the state-wise datasets — all 37 are frozen at 31 March 2021.**
> **Never use `CompanyIndian/Foreign Company`** — ~670k rows contain the literal
> string `91`, a phone country code leaked into a country field.
>
> The API 502s under sustained load (~20 calls in, everything goes dark including
> requests that worked seconds earlier). So the MCA pull is a **cached snapshot
> refreshed rarely**, with backoff and retries, never an inline dependency of the
> nightly build. A dead MCA upstream must degrade to "no badge", never fail the run.

### 10. The site
Search, sort and filter over the JSON; row click reveals roles, links and badges.
Filters: hiring city, remote-only, funding bracket, last-round recency, MCA-verified.

**Acceptance:** loads with zero console errors and zero failed network requests;
filtering to a city yields only companies with a role in that city; the snapshot
date is visible on the page.

### 11. Tiered refresh
GitHub Actions: **Greenhouse nightly** (0.35s/company), **Ashby weekly**
(~151s/company fixed, concurrency ~12 with backoff and retries).

**Acceptance:** both workflows complete inside the 6h job cap; a run that fails
leaves the previously published JSON intact rather than committing a truncated file.

### 12. Integrity reporting — the anti-silent-failure feature
A zero must never be ambiguous. Distinguish *no India roles*, *slug unresolved*,
*probe failed/throttled*, and *provider returned 200 with an empty array* (the
known Lever trap).

**Acceptance:** every build emits `build-report.json` with a count per outcome;
a company that was never successfully checked is **excluded** from the site and
counted as `unchecked`, never rendered as "not hiring". The site footer shows how
many companies were checked and how many could not be.

### 13. Hiring velocity — trend from git history
The nightly workflow already commits `data/companies.json` to a git repo, so the
repo **is** the time series. Derive per-company trend by walking `git log` on that
one file. No database, no new storage, no backfill.

Each company gains `reqs_30d_ago` and `trend` ∈ `ramping | flat | cooling | new |
insufficient-history`, rendered as a sparkline with a "ramping" filter.

**Acceptance:** a company whose India req count strictly increased across
snapshots shows `ramping` and appears under the ramping filter; a company with
fewer than the minimum number of usable snapshots shows `insufficient-history`
and **never** a fabricated trend.

**Hard constraint — trend is computed ONLY over snapshots where that company was
successfully checked.** A snapshot in which the company was `unchecked` (feature
12) contributes **no data point**, never a zero. Without this, every Ashby 502
manufactures a phantom collapse, and a confident wrong trend is materially worse
than no trend — it misdirects a real career decision.

**Depends on feature 12.** Velocity is only as honest as the snapshots beneath it,
so integrity reporting is a prerequisite, not a parallel nice-to-have.

> This was adopted from the out-of-the-box step and **reverses a deferral** made
> earlier in this spec. The original reasoning — "historical tracking needs the
> persisted state statelessness buys us out of" — rested on a false premise: git
> is already a persisted store, obtained free as a side effect of committing the
> nightly JSON. The deferral was priced wrong, not decided wrong. Statelessness
> of the *build* is preserved; only the *reader* looks backwards.

---

## Non-goals

- No backend, database, user accounts, or saved searches.
- No director/DIN data. MCA publishes it; it is personal data and helps no one here.
- No job-application features — we link out, we never proxy an application.
- No paid data sources (Crunchbase, Tracxn, Tofler) in v1.
- No non-software sectors, no hardware, no biotech, no services firms.
- No scraping of MCA21 itself; `mca.gov.in` returns 403 and we respect that.
- No claim of completeness. The site shows what it could verify, and says so.

## Deliberately not building yet

- ~~**Historical tracking / trend charts.**~~ **Promoted to feature 13** — the
  deferral assumed history needs a store we don't have; git already is one.
- **Email / RSS alerts on trend changes.** The obvious sequel to feature 13
  ("tell me when a company starts ramping"). Deliberately held back until trend
  data is proven trustworthy over a real month of snapshots — alerting on a
  phantom trend is the worst version of this product.
- **More ATS providers** (Workday, SmartRecruiters, Lever EU, in-house boards).
  Add when the resolution rate plateaus and these are the measured gap.
- **Fuzzy-matching infrastructure.** Hand-maintained overrides until the override
  file gets painful. A matching framework before that is speculative.
- **Email alerts / RSS.** Real value, but it needs the history layer above.
- **Automated slug enumeration by crawling ATS namespaces.** Interesting, and a
  project of its own.

---

## End-to-end verification scenario

The single scenario that proves the whole thing works:

1. Run the full build from a clean checkout.
2. `data/companies.json` is produced, non-empty, and schema-valid.
3. Pick any company in it. It has ≥1 open India role, and that role's apply URL
   returns 200 on the company's real posting.
4. Pick a company NOT in it that has a resolved slug. `build-report.json` states
   why — `no-india-roles`, not `unchecked`.
5. Open the site. Zero console errors, zero failed requests.
6. Filter to "Bengaluru". Every result has a Bengaluru role; none has only, say,
   a Warsaw role.
7. The location fixture from Feature 5 passes: `In-Office` is not India.
8. The footer shows checked vs unchecked counts, and they sum to the corpus size.

If all eight hold, the site is telling the truth.

---

## Measured constraints (from `learning-tests/FINDINGS.md`, 2026-07-28)

| Fact | Value | Consequence |
|---|---|---|
| Greenhouse latency | 0.35s, one call, complete | nightly refresh is free |
| Ashby latency | ~151s fixed, payload-independent | weekly only |
| Ashby concurrency | flat wall at 1/4/12 → 16.8s/co at 12 | ~4.7h per 1,000 |
| Ashby throttling | 50s → 151s across three runs | backoff required |
| Ashby failures | 3/12 at concurrency 12 | retries required |
| Lever | 200 + empty array on bad slug | zero ≠ not hiring |
| India match | city list finds 167/4,337; ISO regex adds 0 real | no regex |
| MCA state-wise data | frozen at 2021-03-31 | never use |
| MCA RoC dataset | 3.67M rows, newest reg 2026-03-31 | the only usable source |
| Registered key page size | 10,000/call | full scan = 367 calls |
| Foreign subsidiaries on MCA | **24,102** | the enrichment universe |
| `CompanyIndian/Foreign Company` | ~670k rows contain `91` | field corrupt, unusable |
| MCA API under load | 502s after ~20 calls | cache the snapshot, degrade gracefully |
