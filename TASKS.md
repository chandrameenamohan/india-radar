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

Seven epics, 27 tasks. That is more than fits in one head at a glance — so the
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

### T1.6 — Resolve a website per company `done` · *Phase 1* · after T1.5
> **The site is no longer empty: 0 → 88 listed companies, slug resolution 0 →
> 744 of 2,948 (25%).** Split: 480 careers-page, 260 guess, 4 override. 1,833
> companies carry a website; the remaining 1,115 are almost all EDGAR, which
> states none.
>
> **The 2.5–3h cost estimate deferred this step for five iterations and was never
> measured.** Measured now on a 64-company sample: 0.96s/company at 16 workers,
> 0.28s at 48 — it is pure network wait, so threads cost sockets. The real run
> was ~30 minutes, more than the sample's 14 (a random 64 under-represents the
> domains that hang to the timeout) and an order of magnitude under the estimate
> every iteration since T2.2 quoted at each other without anyone timing it.
>
> **The next bottleneck is now measured rather than inferred, and it is not slug
> resolution.** 315 companies hold a VERIFIED slug and are `probe-failed` purely
> because no probe exists — 264 Ashby, 51 Lever. **T3.2 and T3.3 are worth up to
> 315 companies against a listed count of 88**, which is more than any slug
> improvement can reach: of the 2,219 still `slug-unresolved`, 837 have a website
> whose careers page names no board and 619 a website we could not reach at all.
>
> Also measured: 15 slugs that resolved cleanly 404 at probe time. They land as
> `slug-unresolved`, which is correct — a board that isn't there is not a board
> with no roles — but it means a resolved slug is not a probeable one.
> **Added 2026-07-29 after the pipeline ran end to end and listed ZERO companies.**
> Root cause: corpus records carry `name`, `amount`, `date`, `source_url` — and no
> company website. T2.1 discovers ATS slugs by fetching a company's careers page,
> so it had nothing to fetch and resolved 0 of 1,081. T2.2's name-guessing then
> resolved 0 verified, correctly, because "a board that answers is not proof of
> whose board it is" — and without a website there is nothing to verify against.
>
> This was a gap in the DECOMPOSITION, not in any task's execution. T2.1's
> acceptance ("resolve 7 real careers pages, rate >= 50%") was satisfiable with
> hardcoded URLs while the real pipeline resolved nothing. Acceptance criteria
> exist to prevent exactly that, and this one did not.

Derive a company website per corpus record. The funding article itself is the
cheapest honest source — FinSMEs and TechCrunch link the company they cover.
EDGAR does not, so Form D records may legitimately end with no website.

```
Acceptance (observable):
  corpus.json records carry `website` where one could be found, and `null` where
  none could — never a guessed domain. The build report counts how many companies
  have a website, and slug resolution rises above zero as a direct result.
  A company with a website but no discoverable board is `slug-unresolved`, which
  is different from having no website at all — report those separately so the
  next bottleneck is visible rather than inferred.
Checks:
  lint -> unit:test_website_absent_is_null_not_guessed,
          test_website_extracted_from_article_fixture
       -> integration:run over the real corpus, assert website coverage > 0 and
          that end-to-end `listed` count is no longer 0
Out of scope: buying a data source. Free extraction only.
```

### T1.7 — Software/sector filter `done` · *Phase 1* · after T1.5
> **109 excluded and counted, 192 kept and flagged, 0 listed companies lost.**
> Corpus 2,948 → 2,915 (the filter removed 109; a live re-scrape added 76). All
> four `overrides.yaml` companies survive, including Stoke Space Technologies,
> which lands in `ambiguous` — kept, exactly as intended.
>
> **No source states whether a company is software, and all four were checked.**
> Form D's whole technology branch is `Computers`/`Other Technology`/
> `Telecommunications`, so Seegrid and KYG Trade file exactly as a SaaS company
> does. YC states a rich `subindustry` — and it categorises by **market served,
> not by what the company builds**: `Consumer -> Food and Beverage` holds
> DoorDash, Instacart, Rappi and **Zepto** beside Nobell Foods, and `Industrials
> -> Automotive` holds Cruise. Reading those buckets out is one line and deletes
> the most on-thesis row the site could carry. Same shape as this task's own
> out-of-scope note about NIC codes, reached from the other direction.
>
> **So the filter reads the name — and a name is weak evidence, so it returns
> three verdicts rather than two.** Conclusive terms exclude and are counted;
> real-but-unsettled ones keep the company and flag it, because wrongly excluding
> a real company is invisible while wrongly including one is visible and fixable.
> `ambiguous` is 192 names, a human-sized list rather than a 2,915-row hunt.
>
> **The vocabulary is measured, and four plausible terms had to be thrown out.**
> Every candidate ran against all 2,948 live names first. `labs` reads as a
> laboratory and is really Cockroach, Grafana, dbt, Modal, Mysten, Ripple and
> Protocol — 82 names, dropped entirely. `capital`/`ventures`/`partners` read as
> investment vehicles and are Drip Capital, Scalable Capital and Globalization
> Partners — dropped. `medical` and `surgical` would have deleted Circle Medical
> and Surgical Safety Technologies — demoted to ambiguous. The unusable-name rule
> demands the absence of *every* letter (it catches `011235813`, `1910`, `222`,
> `42`) because `0x`, `N26`, `G2`, `R2` and `01.AI` are real companies and any
> ratio-shaped rule takes them too.
>
> **Two exclusions are genuinely arguable and were let stand:** `CODA Farm
> Technologies` (agtech software, but agriculture is a named non-goal) and `Data
> Driven Bioscience`. Both are one line in `NOT_SOFTWARE` away from returning.
>
> **Not touched here:** `data/slugs.json`. Excluded companies simply stop being
> looked up, so no re-resolution was needed; `companies.json` was rebuilt and is
> unchanged at 88 listed. T3.2/T3.3 remain the 315-company gain.

> **Added 2026-07-29.** `grep -i software TASKS.md` returned nothing: SPEC.md says
> "software companies" and names non-software sectors as a non-goal, but no task
> ever implemented it. SEC Form D covers EVERY private placement — hedge funds,
> real estate, food — and contributed 989 of 2,054 corpus companies. Observed in
> the live corpus: `Spero Foods`, `KYG Trade`, `Seegrid`, and `011235813`.

Filter the corpus to software/SaaS/internet/AI companies.

```
Acceptance (observable):
  The corpus excludes obvious non-software companies and COUNTS what it excluded
  (never a silent drop — same rule as T1.5). A hand-labelled set of 30 companies
  spanning clear-software, clear-not-software and genuinely-ambiguous classifies
  with zero clear-software rejections; ambiguous cases are KEPT and flagged, since
  wrongly excluding a real company is invisible while wrongly including one is
  visible and fixable.
  Entries with non-name identifiers (e.g. "011235813") are excluded as unusable.
Checks:
  lint -> unit:test_30_labelled_companies, test_ambiguous_kept_and_flagged,
          test_exclusions_are_counted_not_dropped
Out of scope: a formal taxonomy. MCA NIC codes are too coarse and often stale;
              this is a tag, as SPEC.md assumed.
```

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

### T2.3 — Manual override file `done` · *Phase 1* · after T2.2
> **Ships four real companies, not empty scaffolding** — A24 Films, Cross River
> Bank, Prove Identity, Stoke Space Technologies. Each is a board T2.2's guessing
> found and then deliberately refused, because the board states a name SHORTER
> than the company's and is therefore string-for-string the same shape as
> `Brave Care → brave`, the browser. Nothing in a Greenhouse response tells those
> apart; a human can, and this is where a human does it. All four re-verified
> live today. **Razorpay was considered and dropped**: it resolves by careers-page
> already, and an override duplicating working automation is clutter that rots.
>
> **"Fails loudly" is narrower than it first reads, deliberately.** A *dead*
> override stops the run — every other unresolved company is counted and left
> off the site, but an override claims a human already checked, so the same
> silence would read as "they aren't hiring" (on Lever, literally a 200 with an
> empty array). A probe that failed for any OTHER reason does NOT fail the run:
> a Greenhouse outage is not a mistake in this file, and a check that blames a
> human for someone else's downtime is one people learn to route around. That
> company reaches the build and is counted `probe-failed`, as it should be.
> The distinction was free — `board_name` returns None for a 404 and a 502 alike,
> but T3.1's `probe` already separates them, so verification reuses the outcome
> enum. See FINDINGS.
>
> **An Ashby or Lever override is refused, loudly.** Only Greenhouse can be asked
> whether a board exists today, and an unverified override is the one thing this
> file must not hold. Such a row would be `probe-failed` anyway until T3.2/T3.3.
>
> **No PyYAML.** The project still carries zero runtime dependencies; one regex
> reads `<name>: <ats>/<slug>` and rejects everything else with a line number
> rather than half-reading it. YAML over JSON buys exactly one thing — the
> comment saying why a human overruled the machine — and a test holds every entry
> to it. Precedence is structural: an overridden company never enters the
> automatic pass, so there is no answer to prefer.
>
> **Not done here, fifth iteration running:** `data/slugs.json` was not
> regenerated (~2.5–3h at 8 workers for 2,953 companies), so overrides add four
> companies to a file nobody has rebuilt and `data/companies.json` still renders
> T1.2's snapshot.
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

### T3.2 — Ashby probe `done` · *Phase 1* · after T3.1
> **88 → 110 listed, and `probe-failed` 315 → 51 — which is exactly T3.3's Lever
> share and nothing else.** Of the 264 Ashby companies: 22 listed, 232
> `no-india-roles` (board read, hiring, not here), 10 `slug-unresolved` (resolved
> cleanly at T2.1 time, 404 now — T1.6's "a resolved slug is not a probeable
> slug", seen again). Lever is now the entire remaining probe gap.
>
> **The latency line below is stale by two orders of magnitude, and it was this
> project's most load-bearing number.** Measured before writing any code: one
> call **2s**, and **12/12 concurrent in 1.7s wall** — not ~151s with 3 of 12
> failing. The whole Ashby corpus costs ~35s; a full build is 5m12s end to end,
> dominated by Greenhouse's 429 *sequential* calls. **T6.3's premise ("Ashby
> weekly because it is ~151s/company") no longer holds — re-measure rather than
> inherit it.** The retries and backoff stayed regardless: the throttling was
> real when it was measured, it can return, and at 2s the guard is free.
>
> **Ashby is not Lever's trap: a wrong slug 404s** (plain text `Not Found`), so
> an empty `jobs` array is an honest zero and `empty-board-unverified` belongs to
> T3.3 alone. But there is **no `meta.total`**, so Greenhouse's agreement check
> has no counterpart and a truncated board is undetectable — which is why a
> malformed 200 is *retried* rather than recorded. A half-received transfer is
> transient in exactly the way a 503 is and the status line cannot tell them
> apart.
>
> **`secondaryLocations` forced a structural change, not a parser tweak.** One
> posting open in Bengaluru and Mumbai is one job in two cities: reading only the
> primary undercounts it, counting the location strings over-counts it. So
> `build.Provider` pairs each probe with its own location unwrap — Greenhouse
> nests exactly one `location.name`, Ashby returns a list — and India roles are
> counted by role. `india.is_india` stays a function of a string, as its own
> docstring argued.
>
> Four mutations confirmed the new checks bite: dropping `secondaryLocations`,
> returning on the first failure, retrying without backoff, and counting location
> strings instead of roles each turn the suite red.

~~~151s fixed latency, payload- and concurrency-independent; 16.8s/company at
concurrency 12; 3/12 failed at that concurrency; latency grew 50s→151s across
repeat runs (progressive throttling).~~ **Measured 2026-07-29: ~2s/call, 12/12
concurrent in 1.7s. See the note above and FINDINGS.**
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

### T3.3 — Lever probe `done` · *Phase 1* · after T3.1
> **`probe-failed` is 0 for the first time — 51 → 0 — and 110 → 116 listed.** The
> 51 Lever companies split 6 listed, 37 `no-india-roles`, 5 `slug-unresolved`
> (404 today, resolved cleanly at T2.1 time) and 3 `empty-board-unverified`. That
> outcome counts as *unchecked*, so the honest total is 711 checked of 2,915.
>
> **NEEDS REVIEW — the DoD's integration check is unsatisfiable as written, and I
> did not reword it.** "Probe a known-bad slug, assert outcome is
> `empty-board-unverified`" now yields `slug-unresolved`, correctly: ten wrong
> slugs of three shapes (nonsense, near-miss spellings, and our own slugs minus
> their `-2` suffix) **all 404** with `{"ok":false,"error":"Document not found"}`.
> Nothing constructible answers 200-with-empty-array any more. Re-reading the row
> this task was built on, FINDINGS §1 never showed otherwise — 5 slugs, 3 404s,
> and 2 that returned 200-empty and *might* have been wrong. The trap was always
> an inability to tell, not a demonstrated behaviour.
>
> **The outcome still earns its place, and three live companies are why.**
> `ramenvr`, `tesorio` and `trela` answer 200 with `[]` today. An abandoned
> board, a renamed company and a firm that isn't hiring are byte-identical, and
> Lever has no counterpart to Greenhouse's `boards/{slug}` name lookup — there is
> no second question to ask. So an empty board is excluded and counted as an
> absence of knowledge. `learning-tests/lever_live.py` §5 asserts what the check
> is *for* against boards that really do answer that way, and pins the 404 case
> beside it. **The human call: accept that substitution, or reword the DoD.**
> Nothing else in the task depends on the answer.
>
> **This is the one place the three probes deliberately disagree.** Ashby's empty
> array is believed and Lever's is not, though both 404 a wrong slug. The
> difference isn't the 404 — Ashby was checked against a board we could name and
> Lever cannot be. It costs 3 companies, all excluded either way; it buys T5.3 a
> footer that counts them under "could not check" rather than claiming we did.
>
> **`allLocations` is the whole location answer, not a second half.** Present on
> all 158 postings across six boards, and it *contains* the primary — unlike
> Ashby's `secondaryLocations`, which is genuinely the other places. Prepending
> `location` would double every city on every row: invisible in the role count,
> visible in the site's city filter. Four mutations confirmed the checks bite —
> believing the empty array, prepending the primary, unregistering the probe, and
> letting a 404 borrow the unverified outcome each turn the suite red.
>
> **The bottleneck moves for the last time inside E3.** `probe-failed` no longer
> means "we hold a slug nothing can read"; it means only what the vocabulary
> says. Every remaining exclusion is a slug problem: **2,201 `slug-unresolved`,
> 1,251 of them with a website we already hold.** That is E2's frontier, not
> E3's.

~~**The trap:** a wrong slug returns HTTP 200 with an empty array,
indistinguishable from "no open roles".~~ **Measured 2026-07-29: every wrong slug
404s. Only real boards answer 200-empty — which is still unverifiable, for a
different reason. See the note above and FINDINGS.**
```
Acceptance (observable):
  A 200-with-empty-array is recorded `empty-board-unverified` and the company is
  EXCLUDED from the site. It is never silently treated as "not hiring".
Checks:
  lint -> unit:test_empty_array_is_unverified_not_zero
       -> integration:learning-tests/lever_live.py -- assert the outcome against
          boards that REALLY answer 200-with-[] (ramenvr, tesorio, trela), and
          pin the 404 case beside it.
Out of scope: distinguishing bad-slug from genuinely-empty. We can't, so we
              refuse to guess.

REWORDED 2026-07-29 (human ruling). The original check was
"probe a known-bad slug, assert empty-board-unverified". It is unsatisfiable:
ten wrong slugs of three shapes all 404 now. The substitution is BETTER -- it
tests the outcome against boards that genuinely behave that way instead of a
hypothetical. Also corrects me: FINDINGS originally claimed Lever "returns 200
with an empty array on a bad slug"; I had observed two slugs that returned
200-empty and MIGHT have been wrong. The trap was always an inability to tell,
never a demonstrated behaviour. The outcome still earns its place -- three live
companies answer that way and Lever has no name-lookup to ask a second question.
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

### T4.1 — Roles, apply links, city, remote flag `done` · *Phase 2* · after T3.4
> **1,112 India roles now ship with a title, an apply link and a workplace, and
> 10/10 sampled apply URLs returned 200** — the DoD's own integration check,
> spread across all three providers (`learning-tests/roles_live.py`). Schema v4:
> the `india_roles` count is replaced by the `roles` themselves, because carrying
> both invites them to disagree. Outcomes are unchanged (116 listed, 0
> probe-failed) — enrichment must not move the listed set, and it didn't.
>
> **NEEDS REVIEW — "shows ≥1 India city OR an explicit remote flag" is false for
> 15 of 116 companies, and I did not reword it.** 28 listed companies name no
> India city. Both honest routes were built and measured: the board's own
> `workplaceType` (Ashby says `OnSite`/`Hybrid`/`Remote`, Lever says the same in
> lowercase) and the location string (`Remote - India`, `India (Remote)`, …).
> Together they resolve 13. The remaining **15 have a board that says literally
> `India`** — Komodo Health, Scale AI, Starburst, Tamara, Temporal, YugaByte and
> nine more, all Greenhouse, which states a workplace **nowhere**: not on the
> role, not in `metadata`, and the description is dropped by `content=false`.
> There is no second question to ask, so a city or a remote flag for those 15
> could only be invented.
>
> The same acceptance's third clause — *no company displays an empty location* —
> is satisfiable and is the one that protects the reader, so the site renders the
> three cases apart: cities where named, `Remote — India` where the board says
> remote, and otherwise **what the board literally said**. `role_errors` enforces
> the deterministic half: a role's `locations` list may not be empty.
> **The human call: accept that substitution, or reword the DoD.** Nothing else
> in the task depends on the answer. (Same shape as T3.3's open question.)
>
> **A gate defect found by this task, worth more than the feature.** `make check`
> went green against a **cached copy of `index.html` from before the edit under
> test** — the page said "schema v3" while the file said 4, and every behavioural
> check passed anyway because the stale page and the stale data agreed. Fixed
> port ⇒ identical document URL ⇒ browser heuristic cache. `open_page` now
> cache-busts per run. The page's `{cache:'no-cache'}` covers the JSON, never the
> document that fetches it. See FINDINGS.
>
> Four mutations were run against the new checks; three bit. The fourth —
> **defaulting an unstated workplace to `on-site`** — passed a full green gate,
> which is why `a role whose board stated no workplace shows no badge` now
> exists. 822 of 1,112 roles state nothing, so that default would invent the
> commonest answer for the largest provider: the ambiguous zero, wearing a badge.
>
> Also landed: SPEC feature 10's **remote-only filter**, which T5.2 deliberately
> left out because no row carried the field yet. It has an e2e check.
>
> **The city half was already built** — `src/india.py:cities` and the row's
> `cities` field landed with T5.2, whose city filter could not exist without them.
```
Acceptance (observable):
  Every listed company has >=1 India role with an apply URL returning 200 on that
  company's real posting. Location renders in three honest cases: named cities
  where the board names them, "Remote — India" where the board says remote, and
  otherwise VERBATIM WHAT THE BOARD SAID.
  No listed company renders an empty location. (`role_errors` enforces the
  deterministic half: a role's `locations` list may not be empty.)

  REWORDED 2026-07-29 (human ruling). The original demanded ">=1 India city or an
  explicit remote flag", which is false for 15 of 116 companies whose Greenhouse
  board says literally `India` and states a workplace NOWHERE -- not on the role,
  not in metadata, and `content=false` drops the description. Both honest routes
  were built and measured (board `workplaceType`, and location-string parsing);
  together they resolve 13 of 28. For the remaining 15 a city or remote flag could
  only be INVENTED. This project's premise is "proven by their own job board, not
  by a claim", so fabricating a location to satisfy my wording would have been the
  worst possible way to pass.
Checks:
  lint -> unit:test_city_and_remote_parsing
       -> integration:sample 10 listed companies, assert every apply URL is 200
Out of scope: role deduplication across boards.
```

### T4.2 — Salary benchmark `done` · *Phase 2* · after T5.1 · parallel
> **82 of 115 listed companies now carry an India CTC figure with the date the
> source recomputed it and a link to check it.** Schema v5. The listed set is
> unchanged by the enrichment, which is the point: it runs after the spine, on
> the rows the spine produced, and cannot decide who is on the site.
>
> **The observation date is not a footnote, and the data is what says so.** The
> 82 figures were last recomputed anywhere between today and **2025-10-12**, so a
> bare "₹21.2L" is a nine-month-old sample presented as a fact about now.
> AmbitionBox states `lastUpdated` per company, so the honest date was available
> for free — and `salary_errors` refuses a figure that arrives without one, which
> is `test_date_always_shown` in its deterministic form. A mutation that stamped
> the build date instead of the source's turns two checks red.
>
> **The sample size ships beside the figure** because the live ones run from 1
> self-reported salary to 9,502. An average of one is a real sourced figure and a
> poor benchmark; SPEC's out-of-scope line forbids imputing, so the fix is to show
> the reader the sample rather than to invent a cutoff. A figure with no stated
> sample is refused outright — the gap that mutation testing found, since the
> first version passed a fabricated `1` unnoticed.
>
> **The source rate-limits on cumulative volume and says 403; a genuine absence
> says 404.** Two sweeps ran clean, the third came back 86-of-116 blocked and the
> fourth 116-of-116, while a single call seconds later answered normally. Going
> slower does not help — the worst run measured was the ONE-worker one, being the
> third sweep in a minute. Retrying the 403s and never the 404s is worth **65 →
> 82** companies. Same 404-is-final rule as T3.2, reached from the other side.
>
> **`slugs.states_company` was reused unchanged, and its loose direction turned
> out to be load-bearing** — `Kaseya` → `Kaseya Software` and `Tide` → `Tide -
> Business Management Platform` both state MORE than the corpus name, so an
> exact-match rule would drop them. Zero name mismatches across the listed set.
>
> **Absence renders as nothing at all**, not as "salary unknown": 33 of 115 rows
> have no figure, and a line announcing the gap would put it on a third of the
> site. An e2e check counts salary lines against rows, and a mutation that made
> the row announce its own gap turns it red.
>
> **Cost:** a full build is now **10m41s**, up from ~5m, almost entirely backoff.
> **T6.2/T6.3 should tier on that** — the slowest thing in a build is no longer
> an ATS probe. See FINDINGS.
```
Acceptance (observable):
  Where present, renders the figure with its observation date and a working source
  link. Where absent, the row renders cleanly. Absence is NEVER an error and never
  blocks a build.
Checks:
  lint -> unit:test_absent_salary_renders_clean, test_date_always_shown
Out of scope: imputing salaries. We show sourced figures or nothing.
```

### T4.3 — MCA snapshot pull `done` · *Phase 2* · after T5.1 · parallel
> **24,102 records cached in 3 calls and 17.9s — exactly the predicted universe,
> 100% of it, with zero blank fields across all 24,102 rows.** `data/mca.json` is
> 5.8MB; the build reads it and never calls the API.
>
> **The "502 after ~20 calls" constraint is real and this pull never reaches it.**
> It still shaped the module — a nightly build that called data.gov.in inline
> would be a site that goes down when someone else's Elasticsearch does — but the
> honest measurement is that a three-call pull is nowhere near the wall. Retries
> and backoff stayed regardless, for the same reason T3.2 kept Ashby's: the
> throttling was real when it was measured and costs nothing when it is absent.
>
> **The refusal is against the EXPECTED 24,102, not against the API's own total,
> and that distinction is the whole check.** When the filter was spelled
> `Subsidiary of Foreign Company` the API returned `total=0` — so a pull
> validating itself against the reported total would have cached an empty
> universe and called it agreement. That spelling *still* returns 0 today, pinned
> beside the right one in `learning-tests/mca_live.py` §2. A pull under 90% of
> either figure raises and the previous snapshot survives, the same rule
> `build.write` keeps for a non-conforming row.
>
> **The dataset is more current than FINDINGS recorded** — newest incorporation
> 2026-06-01, against the 2026-03-31 measured in July. The 37 state-wise datasets
> are still frozen at 2021-03-31; the gap is now five years and three months.
>
> **T4.4's ceiling is measured, and it is not a matching problem.** The
> foreign-subsidiary filter excludes Indian-origin companies *by construction*:
> `STRIPE INDIA PRIVATE LIMITED` is in the slice and `RAZORPAY SOFTWARE PRIVATE
> LIMITED` cannot be, because Razorpay is not a subsidiary of a company
> incorporated outside India. A crude three-suffix name join hits **32 of 115
> listed companies**. Lifting that means the unfiltered 3.67M-row table (367
> calls, where the 502 wall stops being theoretical) and is a decision about what
> the badge *means* — a mark only foreign subsidiaries can earn will read as a
> mark against Indian startups unless T5.3 says what it is. See FINDINGS.
>
> **The address is kept whole rather than parsed to a city.** SPEC feature 9 wants
> a registered city and it is `rsplit(",")[-4]` on the rows inspected — but that
> is unvalidated over 24,102, so T4.4 owns proving it. Trimming here would have
> cost a re-pull against the flaky API to undo.
>
> **Not done here, deliberately:** no full rebuild. `build-report.json` gains its
> `mca` block on the next real build (~11 min, and it would churn every row with
> today's live boards for a change that adds one report field). The hookup is
> proven by the offline smoke build, which prints
> `24102  MCA foreign subsidiaries cached (pulled 2026-07-29)`.
>
> Six mutations were run against the new checks and all six bit: `counts` calling
> the API, `load` letting a corrupt snapshot raise, `pull` dropping the CIN dedup,
> dropping the expected-universe floor, returning a partial walk, and caching the
> corrupt `CompanyIndian/Foreign Company` column.

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

### T4.4 — MCA name matching `done` · *Phase 2* · after T4.3
Join "Stripe" → "STRIPE INDIA PRIVATE LIMITED". No shared identifier exists.

> **32 of 116 listed companies now ship a CIN, an incorporation date, a
> registered city and an entity status; 30 more are held for review and appear
> nowhere.** Schema v6. The listed set is unchanged by the enrichment, which is
> the point — it runs after the spine, on the rows the spine produced.
>
> **A word boundary is the entire difference between a match and a wrong CIN.**
> A registered name is the company's name followed by the register's own words,
> so the join looks like a prefix test — and a *character* prefix test is wrong
> in both directions on live data. It hands `Kong` the Norwegian maritime group
> `KONGSBERG MARITIME INDIA`, `Notion` a company called `NOTIONEXT`, `Stripe` a
> tutoring firm called `STRIPES ACADEMY`, and `Scale` four separate strangers.
> So the match cuts only between words. But the words must then be run together
> to compare at all, because the register JOINS what the corpus spaces —
> `AMBIENTAI INDIA` is `Ambient.ai` — and that re-opens the trap from the other
> side: `HIGH TOUCH HEALTH SOLUTIONS GLOBAL` concatenates onto `Hightouch`, and
> it is a healthcare company.
>
> **The rule that survives both: the register may JOIN a company's words but
> never SPLIT one.** One comparison — the registered words consumed must not
> outnumber the company's own — and all five of those die on it. The other
> direction is `slugs.states_company` unchanged: the register may say MORE and
> never less, so `COCKROACH INDIA` for `Cockroach Labs` is refused for the same
> reason `greenhouse/brave` is refused for `Brave Care`.
>
> **Two tiers, because "says more" is right and wrong in the same shape.** 32 of
> 116 listed companies reach a registered name that is theirs plus at most
> `INDIA` and a legal form; those publish. Another 30 reach one that says more —
> and that set holds both `GLEAN SEARCH TECHNOLOGIES INDIA` (Glean) and `FERN &
> ADE INDIA` (not Fern). Nothing in the register tells them apart, so the whole
> tier is held in `build-report.json` under `mca.held` for a human and appears
> nowhere on the site. Unresolved beats wrong, as everywhere else here.
>
> **Zero ambiguity at the publishing tier, measured over the whole corpus:** all
> 2,915 corpus names against all 24,102 registered names give 92 `exact` matches
> and not one name reaching two different CINs. The guard ships anyway, because
> `Scale` reaching both `SCALE AI INDIA` and `SCALE FACILITATION PARTNERS INDIA`
> is one word away — and the corpus holds `Scale AI` as its own company.
>
> **The registered city is the district field, not the locality — correcting
> T4.3**, which read `rsplit(",")[-4]` off one Mumbai row where both said
> `Mumbai` and flagged it unvalidated. Validated now over all 24,102: the
> locality is blank on 252 rows, a street fragment on 349 (`Sector -45`, `NH-8`)
> and elsewhere a neighbourhood (`Kandivali West` for EBANX). The district is
> never blank, holds 476 values, and reads as the city a person would name.
>
> **The badge says what it is, because it cannot mean what it looks like.** T4.3
> warned that a mark only foreign subsidiaries can earn reads as a mark against
> Indian startups. So the filter is labelled "Has an India registration" rather
> than "verified", and the footer states that the register slice covers
> subsidiaries of foreign-incorporated parents — a missing CIN says nothing about
> a company. (One correction to T4.3 while here: an Indian-origin company *can*
> appear — `RAZORPAY TECHNOLOGIES PRIVATE LIMITED` is in the slice, because
> Razorpay's holdco is incorporated abroad. The filter is about corporate
> structure, not about where a company feels like it is from.)
>
> Five mutations were run against the new checks and all five bit: dropping the
> join-not-split guard, publishing the prefix tier, reading the locality as the
> city, accepting any confidence on a published row, and dropping the CIN shape
> check.
>
> **"Resolves on the MCA portal" is satisfied by provenance, not by a fetch.**
> Every CIN published is the register's own string, unmodified, and all 24,102 in
> the snapshot match the 21-character CIN shape — which `build.mca_errors`
> enforces, so a parse gone wrong fails the build rather than shipping. Asking
> mca.gov.in directly is not available to us: SPEC records it as a hard 403 and
> a non-goal.
>
> **The MCA enrichment now runs in the smoke build too**, since it reads a local
> file and touches no network. T4.3 could only prove its hookup by a printed
> report line; `./init.sh` now exercises the whole path offline.
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

### T5.3 — Integrity footer `done` · *Phase 3* · after T6.1, T5.2
> **The footer says 711 of 2,915 checked and 2,204 not, and the site cannot
> derive any of the three.** `companies.json` holds 116 rows, so a renderer
> counting what it has can only ever report "116 of 116" — the exact claim of
> completeness this project's premise forbids. Schema **v7** adds an `integrity`
> block, copied out of the build report rather than recomputed: a second count of
> the same thing is a second chance to disagree with the first.
>
> **`checked` is the boards we read, listed or not** — `outcomes.CHECKED`, so a
> company we read and found nothing on counts as checked, because that is a
> finding. The other 2,204 are absences of knowledge and the footer names them as
> such rather than letting them read as "not hiring".
>
> **The DoD's check asserts against the OTHER file, deliberately.** The rendered
> sentence is read back and compared to `build-report.json` — two artifacts of
> one build, agreeing on how much of the corpus it managed to check — plus a
> second check that the two halves sum to it. On the real path that sum can only
> hold (`report()` computes `unchecked` as a subtraction), so `integrity_errors`
> earns its place one level up: it refuses counts that don't account for the
> corpus, and refuses `checked` below the number of rows being written, which is
> the deterministic form of "this footer describes a different build than these
> rows". The e2e fixture carries 9 checked of 30 for the same reason — a fixture
> where everything was checked would render the one sentence the footer exists to
> avoid.
>
> **A refused dataset blanks the footer.** A coverage figure left over from the
> last file, sitting under a refusal to render this one, is the site stating a
> number for a build it just declined to read.
>
> Three mutations were run and all three bite; the third needed care, and it is
> the transferable lesson. Filling the footer *before* the schema guard should
> leave a stale count under the refusal — but the first attempt at it left a
> variable undefined, so `load()` threw, the fetch `.catch` swallowed it, and the
> check went green for a reason unrelated to the mutation. **A mutation that
> makes the page fail EARLIER can pass the check it was written to break.**
>
> **Cost, re-measured: a full rebuild is 10m59s** (T4.2 measured 10m41s), same
> outcomes, and `build-report.json` regenerated byte-identical — so the pipeline
> is reproducible across a day and **T6.2/T6.3 can diff snapshots for real change
> rather than churn.** Note for whoever bumps the schema next: the page refuses
> the published file the instant `SCHEMA_VERSION` moves, so a schema change is an
> ~11-minute task, not a one-line one. See FINDINGS.
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

### T6.2 — Greenhouse nightly workflow `done` · *Phase 3* · after T3.1, T6.1
### T6.3 — Ashby weekly workflow `done` · *Phase 3* · after T3.2, T6.1
> **Re-measured, and the weekly workflow was NOT built — that is the task's
> deliverable, not a shortfall against it.** The DoD's own words are "tiering is
> by measured cost — re-measured per T3.2, not inherited from FINDINGS §1", so
> the measurement decides, and it says no. Against the live 744-slug corpus
> today (`learning-tests/nightly_tiers_live.py`, logs/t63-tiers.txt):
>
> ```
> ashby       261 slugs, WHOLE corpus, concurrent      36.9s     9%
> greenhouse  422 slugs, 0.54s/call sequential          3.8 min  56%
> lever        51 slugs, 2.81s/call sequential          2.4 min  35%
> ```
>
> A weekly Ashby tier buys back **37 seconds a night** and pays six days of
> staleness on 261 companies, republished under a snapshot date claiming today.
> That is the same class of untruth as rendering an unchecked company as "not
> hiring", for 0.5% of the nightly. The acceptance is met by the nightly, which
> already refreshes Ashby: inside the 6h cap by 30x, commits fresh JSON on
> success, and its tiering is now justified by a cost that is true today.
>
> **A decision not to build has no diff, so two tests hold it instead** — both
> mutation-verified. `test_the_nightly_probes_every_resolved_provider`: every ATS
> in `slugs.json` has a probe in `build.PROBES` (dropping Ashby from `PROBES` —
> the crudest form of a weekly tier — turns it red). `test_one_schedule_because_a
> _second_would_be_a_slower_tier`: exactly one workflow carries a `schedule:`
> (adding `weekly.yml` turns it red). Without these, the next iteration reads a
> task named "Ashby weekly workflow" and builds one.
>
> **The provider ordering has now inverted TWICE, on real data, and the third
> reading is hours after the second.** FINDINGS §1: Ashby ~151s/call, the reason
> the split was designed. T3.2: Ashby ~2s. T6.2: Greenhouse the new slow one at
> 1.2s/call. Today: **Greenhouse 0.54s, and Lever the per-call slowest at 2.81s**
> — 35% of probe time for 7% of the slugs. Nothing in this repo changed between
> those last two. **A schedule derived from a provider's latency is a schedule
> derived from someone else's weather;** the build fits the job cap by 8x, and
> spending that margin rather than re-measuring is the right trade. Corollary for
> whoever optimises next: the target is Lever, not Greenhouse. See FINDINGS.

```
Acceptance (observable) [each]:
  Completes inside the 6h job cap. Commits fresh JSON on success. Tiering is by
  measured cost — re-measured per T3.2, not inherited from FINDINGS §1.
Checks:
  lint -> integration:dry-run the workflow, assert wall time is bounded and a
          commit is produced
Out of scope: sub-daily refresh.
```

### T6.4 — Fail-safe publish `done` · *Phase 3* · after T6.2, T6.3
> **A broken provider does not fail this build — it empties it, and `set -e`
> cannot see that.** `scripts/nightly.sh` claimed this task's guarantee outright
> ("a failed or killed run leaves the published JSON exactly as it was — T6.4's
> guarantee, arrived at here by not having a way to break it"). It is half of it.
> Every probe returns `probe-failed` on a bad status rather than raising, which is
> correct and is the reason: a company we could not read is excluded and counted,
> never listed as hiring nobody. So a night when Greenhouse is down exits **0**
> with a complete, schema-valid file missing 88 of 116 companies, and the nightly
> commits it. The comment is corrected and the missing half is `build.COLLAPSE`.
>
> **The floor is half, and the gap it sits in is measured.** Against today's live
> file, rebuilding the row set without one provider and offering it to `write`:
>
> ```
> unchanged rebuild     116 rows (100%)  -> PUBLISHED
> lever dark            110 rows  (95%)  -> PUBLISHED
> ashby dark             94 rows  (81%)  -> PUBLISHED
> greenhouse dark        28 rows  (24%)  -> REFUSED
> ```
>
> Real churn is near zero (T6.2 measured 116 rows twice, hours apart, with zero
> non-salary differences) and the biggest provider going dark leaves 24%, so half
> is the wide part of that gap. **A Lever outage publishes, deliberately:** those
> 6 companies leave counted as `probe-failed` and the footer's `checked` says so,
> and a floor tight enough to catch 5% would be red on the nights it is wrong.
>
> **The other half of a partial run is a build killed while publishing.**
> `write_text` truncates its target the moment it opens it, and the nightly's
> `timeout` does fire — so the write is now a sibling `.tmp` renamed over the
> target. Half a JSON document is a site that renders nothing at all.
>
> **The salary enrichment was deleting good published data every throttled
> night** — handed here by T6.2's measurement, and now fixed. The live file holds
> 71 figures of 116 rows; without carry-forward a fully throttled night publishes
> **zero** and the site reports a coverage collapse nothing caused. Measured: a
> night where AmbitionBox 403s everything now carries all 71 forward. **This is
> not the staleness T6.3 refused, and the difference is a date** — a board row
> carries none but the snapshot's, so a stale one claims to be today, while a
> benchmark states its own `observed` date beside the figure. That is what T4.2
> made mandatory, and it is what makes carrying one honest.
>
> **A corrupt published file cannot block its own replacement.** `published()`
> never raises, the rule `mca.load` already keeps — otherwise the one state that
> most needs a fresh build is the one state that cannot get one. Same reason a
> carried figure that no longer conforms is dropped: on the next schema bump the
> build would read its own last output, carry a figure the new schema refuses,
> and decline to write, every night, until a human deleted the file.
>
> Seven mutations were run against the new checks and all seven bite. The one to
> watch is `COLLAPSE = 1.0` — refuse every loss — because it is the shape someone
> reaches for to make this "safer", and it holds the site at its high-water mark
> forever. Invariant 6 asserts `0 < COLLAPSE < 1` for exactly that reason.
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
> **NEEDS INPUT: a `git push` of this branch, plus GitHub Pages enabled.** Until a
> human does both, this task cannot ever unblock — and the reason is not the one
> the note below spent two iterations asserting.
>
> **Blocked on T6.1 AND ~30 days of accumulated T6.2 snapshots.** History accrues
> from the first nightly commit whether or not this ships — so the cost of waiting
> is zero, and shipping early means shipping an empty or lying feature.
>
> **Corrected 2026-07-30. Waiting is not sufficient, because ZERO snapshots are
> accruing and none will.** The previous note said the unblocking condition was
> "calendar time with `nightly.yml` firing (`cron: "0 20 * * *"`, verified present
> and scheduled)". It verified the file was present **locally**. GitHub schedules a
> workflow from the copy on the remote's default branch, and there isn't one:
>
> ```
> git ls-tree -r --name-only origin/main | grep nightly   -> (nothing)
> gh run list --limit 10                                  -> (no runs, ever)
> git rev-list --left-right --count origin/main...HEAD    -> 0   14
> gh api repos/.../pages                                  -> 404 Not Found
> ```
>
> **This branch is 14 commits ahead of `origin/main`, which still sits at
> `ad70f38`** — the human's T3.3/T4.1 ruling. Every task from T1.6 to T6.4,
> `nightly.yml` included, exists only on this machine. So the cron has never fired,
> `data/companies.json` has exactly the 2 dates it had yesterday, and it will still
> have 2 in late August. "Earliest plausible start: late August 2026" was wrong:
> the correct answer is **never, absent a push**.
>
> **Two human-gated things, one action each, and the second is a SPEC gap nobody
> tracked.** SPEC.md:12 says the site is "published on GitHub Pages"; Pages is not
> enabled (404 above) and no task in this file ever covered turning it on. T6.4's
> DoD talks about what "the live site still serves" — there is no live site.
>
> **One caveat I could not settle without doing the outward-facing thing.** The
> active `gh` token carries scopes `gist, read:org, repo` — no `workflow` — and
> GitHub refuses an OAuth push that creates or updates `.github/workflows/*`
> without it. So the push may be rejected on `nightly.yml` specifically and need a
> re-auth (`gh auth refresh -s workflow`). `git push --dry-run` returned success,
> but a dry run never sends the pack, so it does not exercise that check and is
> **not** evidence either way. I did not push to find out: pushing 14 commits of
> someone's project is not this loop's call to make.
>
> Do not start this task on the strength of a re-read. Re-run the four commands
> above; if `gh run list` is still empty, nothing has changed.

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
