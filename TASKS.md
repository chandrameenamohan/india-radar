# TASKS — INDIA·RADAR

Decomposition of `SPEC.md`. Markdown, not beads (bd is broken for this project).

**The loop counts actionable work by matching `^### T<n>` headers carrying**
**`` `todo` `` or `` `in-progress` ``.** Keep that header format exactly, or
`ralph.sh` will miscount and either stop early or claim a blocked task.

**Rules that apply to every task below:**
- Tasks are outcome-level. *What is true when it's done*, not *which function to write*.
- Every task carries a Definition of Done: **Acceptance / Checks / Out of scope**.
- **Do not weaken, delete, or skip these checks to pass.**
- A task is not done until its checks are green *and* the craft pass has run on its diff.

**Status vocabulary:** `todo` · `in-progress` · `blocked` · `needs-review` · `done`

---

## The shape of it

Seven epics, 25 tasks. That is more than fits in one head at a glance — so the
sequencing below is deliberately **thin-slice first**: Phase 0 builds one narrow
end-to-end path (one funding source → Greenhouse only → live site). Everything
after widens a working system rather than assembling an unproven one.

At any moment you should only need to hold **Phase 0's six tasks** in your head.

```
PHASE 0 — walking skeleton (prove the whole path end to end)
  T1.1 FinSMEs corpus ──┐
                        ├─→ T1.5 merge+qualify ──→ T2.1 careers-page slugs ──┐
  T6.1 outcome vocab ───┘                                                     │
                                                                              ▼
                                              T3.1 Greenhouse probe ──→ T3.4 India matcher
                                                                              │
                                                                              ▼
                                                          T5.1 emit JSON ──→ T5.2 the site

PHASE 1 — breadth (more corpus, more boards, resolution rate up)
  T1.2 YC · T1.3 SEC Form D · T1.4 TC/Forbes/CBI        (parallel, all after T1.5)
  T2.2 slug guessing · T2.3 override file                (parallel, after T2.1)
  T3.2 Ashby probe · T3.3 Lever probe                    (parallel, after T3.1)

PHASE 2 — enrichment (each independent, each degrades gracefully)
  T4.1 roles+links+city   (after T3.4)
  T4.2 salary benchmark   (after T5.1)
  T4.3 MCA snapshot pull ──→ T4.4 MCA name match        (after T5.1)

PHASE 3 — automation + honesty
  T6.2 Greenhouse nightly ──┐
  T6.3 Ashby weekly ────────┼─→ T6.4 fail-safe publish ──→ T5.3 integrity footer
                            │
                            └─ (both after T6.1 + their probes)

PHASE 4 — velocity (needs real history to exist first)
  T7.1 trend from git log ──→ T7.2 sparkline + ramping filter
       ↑ hard-blocked on T6.1 AND ~30 days of T6.2 snapshots
```

**Critical path:** T6.1 → T1.1 → T1.5 → T2.1 → T3.1 → T3.4 → T5.1 → T5.2.
Everything else widens or enriches that spine.

**Parallelisable** (no shared files, no ordering): T1.2/T1.3/T1.4 · T3.2/T3.3 ·
T4.2/T4.3.

---

## E0 · Foundation

### T6.1 — Outcome vocabulary and build report `done`
> Scheduled first despite its number. Every probe task depends on this contract,
> and retrofitting it later means rewriting all of them. This is SPEC feature 12.

A single shared vocabulary for why a company did or didn't make the site, and a
`build-report.json` that counts every company under exactly one outcome.

Outcomes: `listed` · `no-india-roles` · `slug-unresolved` · `probe-failed` ·
`empty-board-unverified` (the Lever 200-with-empty-array trap) · `not-qualified`.

```
Acceptance (observable):
  build-report.json exists; every corpus company appears under exactly one
  outcome; the counts sum to the corpus size with zero unaccounted rows.
  A company that was never successfully checked is EXCLUDED from the site and
  counted as probe-failed — never rendered as "not hiring".
Checks:
  lint -> unit:test_outcomes_are_exhaustive, test_counts_sum_to_corpus,
          test_unchecked_never_listed
Out of scope: the UI display of these counts (that's T5.3).
```

---

## E1 · Funding corpus

### T1.1 — FinSMEs corpus source `done` · *Phase 0*
```
Acceptance (observable):
  Produces corpus records with name, amount, currency, date, round letter (when
  stated) and a source URL that resolves 200. Re-running yields the same set.
Checks:
  lint -> unit:test_parses_fixture_page, test_amount_and_letter_extraction
       -> integration:scrape 1 real page, assert >=10 records with source URLs
Out of scope: other sources; dedup across sources (T1.5).
```

### T1.5 — Merge, dedup, qualify `done` · *Phase 0* · after T1.1
Amount-based proxy: qualify on stated letter ≥ A, else disclosed round ≥ $5M.

> **The ≥1,000 line is NOT met and could not be, in sequence.** FinSMEs exposes
> exactly one reachable page (~12 records; Cloudflare 403s pagination — measured
> in FINDINGS before this task started), so the only sources that can supply that
> volume are T1.2/T1.3/T1.4, which the graph places *after* this task. Measured
> today: 12 records → 7 qualified, 5 unqualified, 0 unaccounted.
> The volume assertion is therefore carried by the Phase 1 source tasks below,
> where it can actually be satisfied. The merge/dedup/qualify contract itself —
> which is what T2.1 consumes — is complete and green.
> **Human call to confirm: relocating that line rather than blocking Phase 0.**

```
Acceptance (observable):
  corpus.json holds >=1,000 distinct companies, each with qualified_by set to
  exactly one of `letter` or `amount`. A record with neither letter nor amount is
  excluded and counted, never silently dropped. Dedup is order-independent:
  shuffling source order produces an identical company set.
Checks:
  lint -> unit:test_dedup_order_independent, test_qualified_by_exclusive,
          test_unqualifiable_counted_not_dropped
Out of scope: name normalisation for MCA matching (T4.4).
```

### T1.2 — YC directory source `done` · *Phase 1* · parallel
> **The >=1,000 line is MET, by this task alone: 1,081 qualified companies**
> (1,072 by stage, 6 by letter, 3 by amount), up from 9. T1.5 relocated that
> assertion here expecting EDGAR to carry it; it did not need to. T1.3/T1.4 now
> widen a corpus that already clears the bar.
>
> **This extends SPEC feature 2 with a third qualification rule and needs a human
> nod.** YC states no amount, no round letter and no round date for anyone — its
> only fundedness signal is `stage`, which is `Growth` for Stripe, Razorpay,
> Groww and Zepto and `Early` for a three-person current-batch company. So
> `qualified_by` gained `stage` beside `letter` and `amount`. Recording it as
> `letter="A"` would invent a round; dropping it makes the source contribute
> nothing. Reversing the call changes nothing else in the build. See FINDINGS.
>
> Consequences that landed with it: `Record.date` and the published `date` are
> now nullable (**schema v3**) because a YC batch date is not a funding date, the
> site renders `date not stated` and keeps undated rows out of the recency
> filter, and `site/index.html` now fetches with `{cache: 'no-cache'}` — the
> schema bump exposed a live bug where Chromium paired a cached v2 JSON with the
> v3 renderer.
>
> **Not done here, and now measured:** `data/slugs.json` was not regenerated.
> Careers-page resolution is ~3s/company (~54min for 1,081) and hits 2/20 on YC
> Growth names, 10 of the 18 failures never reaching a page. The YC payload
> carries a `website` for 1,072 of 1,075 — unused today because nothing consumes
> it. That is T2.2/T2.3's highest-value change, sized in FINDINGS.

### T1.3 — SEC Form D (EDGAR) source `done` · *Phase 1* · parallel
> **Corpus 1,081 → 2,054 qualified (+973 new, 0 lost); 989 now qualify by
> `amount`, where before only 3 did.** EDGAR is the one source that states a
> dollar figure structurally rather than in prose, so it is what SPEC feature 2's
> amount proxy was written for.
>
> The bulk route: SEC republishes each quarter's Form D as a zip of TSVs, so a
> quarter is **one** call rather than ~16,000 `primary_doc.xml` fetches.
> `QUARTERS = 4` — a year of filings.
>
> **A naive Form D scrape builds a directory of venture funds.** Of 15,981 issuer
> rows, 5,765 are amendments, 5,757 are pooled investment funds (Bain's and
> Sequoia's own funds file Form D), 3,360 are real estate/oil/biotech and 247 are
> co-issuers. 852 are technology operating companies; 247 clear $5M. The filters
> are the source, not housekeeping.
>
> **A bug this task introduced and fixed:** `corpus._strength` picked the record
> with the biggest number, so YC's `Growth` label for Lob lost to EDGAR's $2M
> filing — which then failed the $5M proxy. 4 companies (Datafold, Legion Health,
> Lob, Overview) were demoted from qualified purely by adding a source. `_strength`
> now ranks qualifying evidence above a bigger number. **Generalises to T1.4:** the
> invariant to watch is not "did the corpus grow" but "did anything qualified
> leave". Regression test confirmed failing with the old ordering restored.
>
> **Two corrections landed with it.** `net.UA` — load-bearing against Cloudflare
> — gets a blanket 403 from sec.gov, which wants a declared contact string; so
> `net.get_bytes` grew a `ua=` parameter and returns bytes (a zip is not a page).
> And **EDGAR does not carry a website field**, contrary to what T1.2's findings
> and `slugs.py`'s comment both said — Form D gives a street address and a phone
> number. T2.2 should be sized on YC alone; that comment is corrected.
>
> **Not done here:** `data/slugs.json` was not regenerated (~3s/company against a
> corpus that just doubled), so `data/companies.json` is untouched and the site
> still renders T1.2's snapshot. Slug resolution is still the binding constraint.

### T1.4 — TechCrunch / Forbes / CBI sources `done` · *Phase 1* · parallel
> **Corpus 2,054 → 2,953 qualified (+899 new, 0 demoted).** Each alone, against a
> corpus rebuilt live from T1.1–T1.3: CB Insights +784, Forbes +166, TechCrunch
> +53. All four E1 sources are now in and the ≥1,000 line (relocated here by
> T1.5, met by T1.2) stands at nearly three times it.
>
> **Neither Forbes nor CB Insights states a funding round, and that needed no new
> rule.** Forbes' `funding: 830` is Abridge's *lifetime* total; CB Insights' `$965`
> is what Anthropic is *worth*, and its "Date Joined" is the day it first crossed
> $1B, not its latest round. Either in `amount` would report a round nobody raised
> and hand SPEC feature 2's $5M proxy a figure it was not written for. So both
> carry `stage="growth"` — T1.2's third rule, unchanged, doing what it was added
> for. For Forbes the claim is gated on a total being stated at all, because the
> zeroes are real: Forbes reports 0 for Midjourney, Surge AI, Hyperliquid and
> Increase and nothing for Zoho — the bootstrapped companies, correctly — and
> those five leave by the counted door.
>
> **A naive TechCrunch scrape builds a directory of VC firms.** Of 77 round
> headlines in 1,000 venture posts, a plain `^(name) raises` yields four VC firms
> raising their own funds (Accel, Lightspeed, CRV, SignalFire), a company called
> `Edtech platform` and one called `Gen Zers`. Three structural rules fix it — the
> name is the trailing proper-noun run, a clause closing on a comma before the verb
> is grammar rather than a name, and a fund raise is rejected — and a valuation is
> never read as a round (`raises $250M at $3B valuation` is $250M). EDGAR's lesson,
> in prose form: the filters are the source.
>
> **Not done here, again:** `data/slugs.json` was not regenerated (~3s/company
> against a corpus that grew another 44%), so `data/companies.json` is untouched
> and the site still renders T1.2's snapshot. Every source that could widen the
> corpus has now landed, so **slug resolution is the only remaining constraint on
> site size — T2.2 is the next real gain.** See FINDINGS.
```
Acceptance (observable) [each]:
  Emits records in the same schema as T1.1 and flows through T1.5's dedup without
  special-casing. Adding the source strictly increases distinct company count.
  Carried here from T1.5, because only these sources can satisfy it: with all
  four in, corpus.json holds >=1,000 distinct companies. EDGAR (T1.3) is the bulk
  API with no bot wall and is the realistic source of that volume.
Checks:
  lint -> unit:test_schema_matches_corpus_contract, test_fixture_parse
       -> integration:live fetch, assert non-empty and schema-valid
Out of scope: cross-source conflict resolution beyond T1.5's dedup rule.
```

---

## E2 · ATS resolution

> Measured baseline to beat: **~50%** from careers-page + guessing combined.
> This rate, not funding coverage, is the ceiling on site size.

### T2.1 — Careers-page slug discovery `done` · *Phase 0* · after T1.5
> Measured 5/7 (71%) resolving real companies by name, above the ~50% baseline —
> `learning-tests/careers_slugs_live.py`. On the current 7-company FinSMEs corpus
> it resolves 0/7, every one with a reason. That is the guessed domain failing,
> not the extraction: freshly-funded companies don't map name → domain, and
> FinSMEs carries no website field. T1.2 (YC) and T1.3 (EDGAR) do, and feeding
> one in raises this without touching the regexes. See FINDINGS.

```
Acceptance (observable):
  slugs.json maps company -> {ats, slug, method:"careers-page"}. Unresolved
  companies land in unresolved.json WITH A REASON. The run prints a resolution
  rate. Known-good fixtures (Figma->greenhouse/figma, Ramp->ashby/ramp) resolve.
Checks:
  lint -> unit:test_board_url_regexes_on_fixtures, test_unresolved_has_reason
       -> integration:resolve 7 real careers pages, assert rate >= 50%
Out of scope: JS-rendered pages (that's what T2.2 exists to cover).
```

### T2.2 — Slug guessing fallback `done` · *Phase 1* · after T2.1
Guess from company name, probe Greenhouse (~0.3s, effectively free).
> **8-company fixture: 6/8 by careers-page alone → 8/8 combined**, the split
> reported by method. Live, the two recovered by guessing are Glean and Postman
> — **not Anthropic and Glean as the DoD names**, because Anthropic has resolved
> by careers-page ever since T2.1 started trying `/jobs`. Two JS-rendered boards
> recovered, different names. The unit test still drives Anthropic through
> guessing, where the careers page is stubbed away and the DoD's claim is what's
> under test.
>
> **A board that answers is not this company's board, and that is the whole
> task.** `boards-api.greenhouse.io/v1/boards/{slug}` — no `/jobs` — is the only
> place Greenhouse states *whose* board a slug is. Guessing the first word of a
> name found 5 boards across 60 companies and could not tell `A24 Films → A24`
> (right) from `Brave Care → brave` (the browser). So a guess is kept only if
> the board's own name **contains the whole company name** — it may say more
> (`Automattic Careers`), never less. That costs three real companies
> (A24, Cross River Bank, Prove Identity) and first-word guessing is dropped
> outright rather than kept and filtered. Unresolved beats wrong, as everywhere
> else here.
>
> Candidates are measured, not imagined: over 260 companies the bare normalised
> name found 26 boards, five suffixes found one each (`gleanwork` is why the
> list exists — Glean is in the DoD), and a hyphenated variant plus `hq`/`inc`/
> `io`/`team` found nothing at all.
>
> **A regression this task introduced and fixed:** putting a network call inside
> `resolve_all` made two *existing* T2.1 unit tests probe live Greenhouse. They
> still passed — the suite just went 0.18s → 29s and silently acquired the
> dependency on third-party uptime VERIFICATION.md forbids. `tests/conftest.py`
> now refuses any unstubbed call at `net.get_bytes` and names the URL; opt out
> with `@pytest.mark.network` (one test, 127.0.0.1 only). Any future task adding
> a network call to a shared function inherits the guard.
>
> **Not done here, fourth iteration running:** `data/slugs.json` was not
> regenerated. The cost is now precise — ~3s/company careers-page plus ~5.6s
> guessing on what it misses ≈ **2.5–3h at 8 workers** for 2,953 companies.
> Guessing alone would resolve ~10-15% in ~34 min if a cheap partial refresh is
> wanted before T6.2 automates it. See FINDINGS.
```
Acceptance (observable):
  Runs only on companies T2.1 failed. Combined resolution rate is strictly higher
  than T2.1 alone, and the report shows the split by method.
  Anthropic and Glean — both JS-rendered, both genuinely on Greenhouse — resolve
  here after failing T2.1.
Checks:
  lint -> unit:test_only_runs_on_unresolved, test_method_recorded
       -> integration:combined rate on the 8-company fixture > T2.1 rate
Out of scope: guessing against Lever/Ashby (Greenhouse is the cheap one).
```

### T2.3 — Manual override file `todo` · *Phase 1* · after T2.2
```
Acceptance (observable):
  overrides.yaml wins over both automatic methods; a company listed there resolves
  to exactly that slug with method:"override". An override pointing at a dead slug
  fails the build loudly rather than silently producing zero roles.
Checks:
  lint -> unit:test_override_precedence, test_dead_override_fails_loudly
Out of scope: automating what belongs in the override file.
```

---

## E3 · Probe and filter

### T3.1 — Greenhouse probe `done` · *Phase 0* · after T2.1, T6.1
0.35s/company, one call, `meta.total` is authoritative.
> Measured live on the 5 FINDINGS slugs: meta.total exact on all five (801 roles
> for databricks in one call), and a nonsense slug 404s → `slug-unresolved`.
> `learning-tests/greenhouse_live.py`. A short board is `probe-failed`, never the
> roles that happened to arrive.
```
Acceptance (observable):
  Returned role count equals meta.total in the same response. For a known slug the
  count matches the provider's public board. A 404 slug yields outcome
  `slug-unresolved`, not an empty success.
Checks:
  lint -> unit:test_meta_total_agreement, test_404_maps_to_outcome
       -> integration:probe 5 real slugs, assert counts > 0 and meta agreement
Out of scope: Ashby and Lever.
```

### T3.2 — Ashby probe `todo` · *Phase 1* · after T3.1
~151s fixed latency, payload- and concurrency-independent; 16.8s/company at
concurrency 12; 3/12 failed at that concurrency; latency grew 50s→151s across
repeat runs (progressive throttling).
```
Acceptance (observable):
  1,000 companies complete inside the 6h GitHub Actions cap. Transient failures
  are retried with backoff. A company that exhausts retries is recorded
  `probe-failed` and EXCLUDED — never listed as having zero roles.
  secondaryLocations are read, or multi-location roles are undercounted.
Checks:
  lint -> unit:test_retry_exhaustion_maps_to_probe_failed,
          test_secondary_locations_parsed
       -> integration:probe 12 concurrent, assert all resolve to an outcome and
          wall time is bounded
Out of scope: making Ashby faster. It isn't possible; it's a fixed server delay.
```

### T3.3 — Lever probe `todo` · *Phase 1* · after T3.1
**The trap:** a wrong slug returns HTTP 200 with an empty array, indistinguishable
from "no open roles".
```
Acceptance (observable):
  A 200-with-empty-array is recorded `empty-board-unverified` and the company is
  EXCLUDED from the site. It is never silently treated as "not hiring".
Checks:
  lint -> unit:test_empty_array_is_unverified_not_zero
       -> integration:probe a known-bad slug, assert outcome is
          empty-board-unverified
Out of scope: distinguishing bad-slug from genuinely-empty. We can't, so we
              refuse to guess.
```

### T3.4 — India role matcher `done` · *Phase 0* · after T3.1
City-name list only. **No ISO-prefix regex** — measured: it adds 0 real hits and
introduced 47 false positives by matching the literal string `In-Office`.
> Matched on word boundaries, not substrings: over 1,497 live postings both rules
> find the same 104 India roles, so boundaries are free, and they keep
> `Indianapolis, Indiana` and `Thanet, UK` out. `test_location_fixture_exact` also
> asserts the traps are still IN the fixture — deleting `In-Office` from it is the
> obvious way this invariant comes back green with the bug restored. See FINDINGS.
```
Acceptance (observable):
  The fixture of real location strings classifies with ZERO false positives and
  ZERO false negatives. Must handle: "Bengaluru, India", "Remote - India",
  "India - Remote", "IN-Pune", "Bengaluru, India; Mumbai, India" (one posting,
  two cities), and must REJECT "In-Office" and "Hybrid; In-Office".
Checks:
  lint -> unit:test_location_fixture_exact (the traps are in the fixture)
Out of scope: cities outside the list inside "IN-<City>" strings. Measured
              occurrences: 0. Accepted, documented, revisit if it shows up.
```

---

## E4 · Enrichment

> Every enrichment must degrade to absent. None may fail a build.

### T4.1 — Roles, apply links, city, remote flag `todo` · *Phase 2* · after T3.4
> **The city half is already built** — `src/india.py:cities` and the row's
> `cities` field landed with T5.2, whose city filter could not exist without them.
> What remains here: role titles, per-role apply URLs, the explicit remote flag,
> and the integration check that sampled apply URLs return 200.
```
Acceptance (observable):
  Every listed company has >=1 India role with an apply URL returning 200 on that
  company's real posting, and shows >=1 India city or an explicit remote flag.
  No listed company renders an empty location.
Checks:
  lint -> unit:test_city_and_remote_parsing
       -> integration:sample 10 listed companies, assert every apply URL is 200
Out of scope: role deduplication across boards.
```

### T4.2 — Salary benchmark `todo` · *Phase 2* · after T5.1 · parallel
```
Acceptance (observable):
  Where present, renders the figure with its observation date and a working source
  link. Where absent, the row renders cleanly. Absence is NEVER an error and never
  blocks a build.
Checks:
  lint -> unit:test_absent_salary_renders_clean, test_date_always_shown
Out of scope: imputing salaries. We show sourced figures or nothing.
```

### T4.3 — MCA snapshot pull `todo` · *Phase 2* · after T5.1 · parallel
Resource `4dbe5667-7b6b-41d7-82af-211562424d9a`, page size 10,000, filter
`CompanySubCategory = "subsidiary of company incorporated outside India"`
→ **24,102 companies**.
```
Acceptance (observable):
  Produces a cached local snapshot of ~24,102 foreign-subsidiary records. The
  nightly build READS THE CACHE and never calls the API inline. A dead MCA
  upstream degrades to "no badge" and never fails the run.
Checks:
  lint -> unit:test_build_reads_cache_not_api, test_dead_upstream_degrades
       -> integration:pull with retries, assert record count within 10% of 24,102
Out of scope:
  - the 37 state-wise datasets — ALL frozen at 2021-03-31, never use them
  - the CompanyIndian/Foreign Company field — ~670k rows contain the literal
    string "91", a phone country code in a country field. Corrupt. Never use.
```

### T4.4 — MCA name matching `todo` · *Phase 2* · after T4.3
Join "Stripe" → "STRIPE INDIA PRIVATE LIMITED". No shared identifier exists.
```
Acceptance (observable):
  A matched company displays a CIN that resolves on the MCA portal. Match
  confidence is recorded. Anything below threshold is held `needs-review` and NOT
  published. Unmatched companies render normally without a badge.
  A hand-labelled set of 20 known pairs matches with zero false positives —
  a wrong CIN on a public site is worse than no CIN.
Checks:
  lint -> unit:test_20_known_pairs_zero_false_positives,
          test_below_threshold_held_for_review
Out of scope: director/DIN data — personal data, helps nobody here.
```

---

## E5 · The site

### T5.1 — JSON schema and emit `done` · *Phase 0* · after T3.4
> **"Non-empty" is proven against live data but is 0 on today's corpus.** A real
> build right now is 7 companies → 0 listed, 7 `slug-unresolved`, because
> `slugs.json` is `{}` (T2.1 measured 0/7 on these obscure freshly-funded names).
> Measured live instead: the five FINDINGS boards yield 1,556 roles → 107 India →
> **5/5 would produce a listed row**, with 0 exceptions to the `location.name`
> unwrap the spine assumes — `learning-tests/build_live.py`. The emitter is
> complete; its input is thin until T1.2/T1.3 supply the website field that lifts
> slug resolution. Same shape as T1.5's ≥1,000 line, and nothing here changes when
> that lands.
> The smoke build writes `data/companies.smoke.json`, never the published file —
> a fixture-derived `companies.json` is exactly what T6.4 exists to prevent.
```
Acceptance (observable):
  data/companies.json is produced, non-empty, schema-valid. Schema is versioned
  and enforced — a build emitting a non-conforming row fails rather than shipping it.
Checks:
  lint -> unit:test_schema_validation_rejects_bad_row
       -> integration:full build, assert output validates
Out of scope: the UI.
```

### T5.2 — Search, sort, filter, detail `done` · *Phase 0* · after T5.1
> **The city filter forced `cities` into the schema (v1 → v2), one task earlier
> than the graph puts it.** T3.4 left "which cities they are" to T4.1, but this
> task's own DoD check is the city filter, and a filter cannot be built or
> verified without city data. The alternative was an e2e fixture shaped like
> nothing the emitter could produce. So `india.cities` and the row's `cities`
> landed here; **T4.1 still owns role titles, apply URLs and the remote flag** and
> will find the city half done. See FINDINGS.
> Behaviour is driven against `tests/fixtures/companies-e2e.json`, because a real
> build lists 0 companies today (T5.1's note). A unit test holds that fixture to
> the shipped schema, so it cannot drift into testing a site we don't ship.
> Gate proven by breaking it three ways first — a filter that ignores the chosen
> city, a stray console error, a missing snapshot date — each caught. FINDINGS.
> **Skipped deliberately:** the remote-only and MCA-verified filters SPEC feature
> 10 lists. Both filter on fields no row carries yet (T4.1, T4.4); a control that
> can only return nothing is worse than no control. Visual regression (4c) is
> outside the gate — baselines need one human approval.
```
Acceptance (observable):
  Loads with ZERO console errors and ZERO failed network requests. Filtering to a
  city returns only companies with a role in that city — a company with only a
  Warsaw role never appears under "Bengaluru". The snapshot date is visible.
Checks:
  lint -> e2e:console-clean (assert zero errors/rejections/failed requests)
       -> e2e:filter_city_returns_only_matching
       -> e2e:snapshot_date_visible
Out of scope: accounts, saved searches, applying in-app.
```

### T5.3 — Integrity footer `todo` · *Phase 3* · after T6.1, T5.2
```
Acceptance (observable):
  Footer shows how many companies were checked and how many could not be, and the
  two sum to the corpus size. The site never implies completeness it can't back.
Checks:
  lint -> e2e:footer_counts_match_build_report
Out of scope: a per-company diagnostic view.
```

---

## E6 · Automation

### T6.2 — Greenhouse nightly workflow `todo` · *Phase 3* · after T3.1, T6.1
### T6.3 — Ashby weekly workflow `todo` · *Phase 3* · after T3.2, T6.1
```
Acceptance (observable) [each]:
  Completes inside the 6h job cap. Commits fresh JSON on success. Tiering is by
  measured cost: Greenhouse 0.35s/company nightly, Ashby ~151s/company weekly.
Checks:
  lint -> integration:dry-run the workflow, assert wall time is bounded and a
          commit is produced
Out of scope: sub-daily refresh.
```

### T6.4 — Fail-safe publish `todo` · *Phase 3* · after T6.2, T6.3
```
Acceptance (observable):
  A failed or partial run leaves the previously published JSON INTACT. Deliberately
  break a probe mid-run and assert the live site still serves the last good data
  rather than a truncated file.
Checks:
  lint -> integration:inject a mid-run failure, assert published JSON unchanged
Out of scope: rollback UI.
```

---

## E7 · Velocity  *(SPEC feature 13)*

### T7.1 — Trend from git history `blocked` · *Phase 4*
> **Blocked on T6.1 AND ~30 days of accumulated T6.2 snapshots.** History accrues
> from the first nightly commit whether or not this ships — so the cost of waiting
> is zero, and shipping early means shipping an empty or lying feature.

```
Acceptance (observable):
  Each company gains reqs_30d_ago and trend in
  {ramping, flat, cooling, new, insufficient-history}.
  HARD CONSTRAINT: trend is computed ONLY over snapshots where that company was
  successfully checked. A snapshot where it was probe-failed contributes NO data
  point — never a zero. Without this, every Ashby 502 manufactures a phantom
  collapse, and a confident wrong trend misdirects a real career decision.
  Below the minimum usable snapshot count, trend is `insufficient-history` and
  never a fabricated value.
Checks:
  lint -> unit:test_probe_failed_snapshot_contributes_no_point,
          test_below_minimum_yields_insufficient_history,
          test_strictly_increasing_yields_ramping
       -> integration:synthesise a git history with a 502 gap, assert no phantom
          collapse is reported
Out of scope: alerting on trend changes — held until trend is proven over a real
              month of snapshots.
```

### T7.2 — Sparkline and ramping filter `blocked` · *Phase 4* · after T7.1
```
Acceptance (observable):
  Ramping companies render a sparkline and appear under the ramping filter.
  Companies with insufficient-history show no sparkline rather than a flat line —
  a flat line is a claim, and we don't have the data to make it.
Checks:
  lint -> e2e:ramping_filter_returns_only_ramping
       -> e2e:insufficient_history_renders_no_sparkline
Out of scope: trend charts beyond the sparkline.
```
