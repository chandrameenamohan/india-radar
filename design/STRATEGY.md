# STRATEGY — who this is for, what it beats, and what the next design round must aim at

*2026-08-04. Every corpus number below was recomputed from the world build
(`buildclone/data/companies.json`, snapshot 2026-08-04) rather than quoted.
Competitor facts are from August-2026 web research, cited inline.*

## The verdict, up front

**"Seconds to find the job in your dream company" is the wrong promise, and the
design rounds failed because they were aimed at it.** Finding was never the
job seeker's bottleneck — LinkedIn returns ten thousand jobs in milliseconds and
Hiring Cafe indexes 3.6M jobs from the same ATS boards this product reads, for
free. The bottleneck is **trust** (is this job real, current, and open to
someone like me?) and **entry** (will a human ever read my application?). This
corpus can answer the first today better than anyone. The founder's own
long-term thesis — referrals through registered partners — is the answer to the
second. The register is not the product; it is the *trust layer that earns the
right to sell the referral*.

The promise that fits the data and the roadmap:

> **Every job here is live on the company's own board — and we can get you a
> person, not a portal.**

The first half is buildable this quarter. The second half is the business.

---

## 1. What the corpus actually is (recomputed, not quoted)

| Fact | Value | Consequence |
|---|---|---|
| Companies · roles | 789 · 27,689 | Real, verified, but small: Hiring Cafe indexes ~116,000 companies |
| Funding-corpus coverage | 832 of 2,925 corpus companies checked; **2,093 unchecked** | "Your dream company" is absent ~2 times in 3 even within our own universe |
| Marquee-name spot check | OpenAI, Anthropic, Stripe, Airbnb, Notion, Databricks ✓ — **Figma, Canva, Mistral, Revolut ✗** | A dream-company lookup will miss household names; absence must render honestly |
| US roles (untagged, string-matched) | ~13,200 ≈ 48% | The world build's center of gravity is the US, led by SF (~4,900 role-locations) and NYC |
| 15-country tagged roles | 6,452 (UK 2,011 · India 1,152 · Germany 768 …) | The old radar is now a quarter of the corpus |
| Openness (`visa`/`hire_from_abroad` = yes) | **1,891 roles at 96 companies**; explicit no on ~1,000; **89.8% of roles carry no signal at all** | The cross-border promise is provable for ~7% of the corpus |
| Workplace | remote 5,748 · hybrid 4,013 · onsite 3,439 · **unknown 14,489 (52%)** | Half the corpus can't answer "can I work from home" |
| Department | known for 99%+; Engineering ≈ 6,400, Sales ≈ 2,100 | The corpus is all-function, not an engineering board — a real breadth advantage |
| Funding metadata in world build | amount on 122 of 789; round letter on 5 | "Funded startups" is currently an admission rule, not a displayable fact |
| First-seen | 6,650 URLs dated; only **7 confirmed-new** on 08-04 (world build: 7 dated URLs — the fold hasn't run on the new corpus yet) | Freshness claims are honest but one nightly old at world scale |
| Job description text | **not stored** (fetched per-posting on demand) | Resume matching / semantic search is not buildable this quarter without F1 |

Two facts to hold onto: the corpus is **verified but narrow**, and its single
most distinctive column — the openness signal with honest `no` and `unknown` —
is populated for one role in ten.

---

## 2. Customer segmentation

Segments that would drive *different product decisions*, ranked by how well
today's corpus serves them. "Pays" means demonstrated willingness to pay in the
2026 market, not hope.

### S1 — The US-metro startup seeker (serve NOW; the beachhead)

Mid/senior professional targeting funded startups in SF/NYC/Seattle. Uses
LinkedIn (and pays $30–40/mo for Premium in bursts), Wellfound, increasingly
Hiring Cafe. **Their top pain in 2026 is documented and worsening: 20–33% of
listings are ghost jobs (≈27% on LinkedIn per a Sept-2025 analysis), and
AI-flooded applicant pools mean 500+ applicants per visible posting.**

- **Would switch for:** a board where every posting is provably live on the
  company's own ATS *today*, with a first-seen date and a hiring-momentum
  signal — i.e., "stop wasting applications on corpses." Ontario already
  legislated against ghost postings (Jan 2026); CA/NY are exploring it. This
  pain has regulatory confirmation.
- **Would pay:** modestly and briefly ($10–30/mo, churns on hire) — but pays
  *readily* for a warm intro. Referral demand is proven: refer.me claims 12k+
  seekers paying insiders for referrals; referral bonuses run $5–25k.
- **Corpus fit:** best of any segment — ~48% of roles, all functions, the
  funded-startup universe is exactly their target list. **This is the segment
  the world rebuild silently chose.**

### S2 — The cross-border aspirant (serve as a NICHE now; the pitch's segment)

The person the founder's pitch describes: in India, Brazil, Nigeria, Korea,
wanting into a dream startup abroad. Highest motivation, highest tolerance for
friction, demonstrated payment ($15/mo for relocate.me's newsletter of ~100
hand-curated relocation jobs/week; ~4,800 curated in a year).

- **The honest math:** this corpus holds 1,891 stated-open roles at 96
  companies — **which is already the same order of magnitude as the
  hand-curated market leader.** As a *niche product* ("the register of
  companies that say, on their own board, they'll take you"), it is servable
  today. As "any dream company anywhere," it is not: 90% silence.
- **Would pay:** yes — this is the segment with relocate.me-proven
  subscription behavior and life-changing stakes.
- **Product decision it forces:** lead with the openness filter and the
  explicit-`no` (nobody else indexes negatives — a stated "cannot sponsor"
  saves this person a week). The bilingual-vocabulary and
  `hire_from_abroad`-extraction work (FINDINGS §2–3) is *this segment's*
  roadmap, and it lives in the build, not the renderer.

### S3 — The in-country non-US seeker: India and UK (serve now, differentiate later)

India (1,152 roles + salary benchmark + MCA badge) and UK (2,011 roles +
Companies House badge) are the only countries with enrichment moats. Local
competition (Instahyre/Cutshort in India; Otta/WTTJ owning the UK/EU corridor)
is entrenched. Keep serving; don't lead with it. The MCA/CH verification badges
matter more here than anywhere — fake-employer fraud is a documented
in-country pain the incumbents don't address.

### S4 — The remote-anywhere seeker (roadmap, not customer)

5,748 remote roles, but "Remote (United States)" dominates; remote ≠
hire-from-anywhere, and workplace is unknown on 52% of roles. Serving this
segment honestly requires the same openness extraction as S2. Do not market to
them yet — a "remote" filter that quietly includes US-only roles burns the
exact trust the product sells.

### S5 — The volume applier / new grad (deliberately NOT a customer)

Wants auto-apply, tailored resumes, 300 applications a week. Served by
JobRight ($29/mo), Simplify (free + $39.99/mo), Sorce (swipe-to-auto-apply),
LazyApply-class tools. **The doctrine already refuses this segment** (nothing
auto-submitted, no drafting, no detector-evasion — SPEC v4 non-goals), and it
should keep refusing: this is a commoditized arms race that is *why* recruiters
now distrust applications, and being on the other side of it is the brand.
Write this down as a decision so it stops being relitigated.

**Segment decision for next quarter: build for S1 with S2 as the named
expansion.** S1 is the only segment the corpus serves at competitive scale
today; S2 is the only one with proven subscription payment and is the pitch's
soul — served as a niche register, not a promise of "anywhere."

---

## 3. Competitive map (researched August 2026)

| Competitor | Genuinely good at | Genuinely fails seekers at | Threat to us |
|---|---|---|---|
| **LinkedIn** ($30–40/mo Premium; AI job match, Top Choice, Hiring Assistant for recruiters) | Network, recruiter reach, scale; AI match explanations | ~27% ghost listings; 500+ applicant pileups; monetizes *posting* volume, so it cannot purge stale ads | Structural non-copier of honesty (see below) — but owns S1's habit loop |
| **Indeed** | Volume, SMB reach | Same ghost/stale economics; startup-blind | Low for this audience |
| **Hiring Cafe** (free; 3.59M jobs, ~116k companies, 46 ATS platforms, employer-side monetization) | **Exactly our sourcing method at 130× company scale**, 80+ structured fields, loved by power users | No verification *doctrine*: no first-seen/confirmed-new discipline, no checked-vs-unchecked honesty, no openness negatives, no funded-startup curation; reviews call it "free, clean, but slow" | **The most important competitor.** It proves board-scraping is not a moat — and proves the free-to-seeker model works |
| **Wellfound** | Startup-native; salary + equity mandatory; one-profile apply | Coverage decay (companies drift off), stale postings, spam applicant pools | Owns the phrase "startup jobs"; weak on truth-of-listing |
| **Otta → Welcome to the Jungle** | Curation, culture data, EU corridor dominance | Small inventory by design; no provenance claims; US thin | Owns S3-UK/EU mindshare |
| **YC Work at a Startup** | 1,000+ vetted YC companies, founder-direct contact | YC-only universe; sparse non-engineering | The model to study: *curated universe + direct human contact* — it's the closest thing to our referral thesis |
| **JobRight / Simplify / Teal / Sorce** ($0–40/mo) | Application mechanics: autofill, tracking, tailoring, auto-apply | They *worsen* the flood; none verify listings; none get you a human | Different layer; possible future channel partners, not rivals for the register |
| **relocate.me / Japan Dev / Global Move** ($15/mo proven) | Hand-verified relocation promises; S2 trust | Tiny volume (~100/wk), manual, single-region | Proof of S2 payment; our openness signal at 1,891 roles already rivals their inventory |
| **refer.me / FindMyReferral** | Proven demand for paid referrals (12k+ seekers, escrow) | Trust is thin (unverifiable insiders); ToS/legality gray; no job-truth layer | Proof of the referral business; none has a verified register to anchor it |

### The conclusion the founder needs to hear

**"Provenance — scraped from the company's own board" is NOT the moat. Hiring
Cafe already does it, free, at 130× scale.** Anyone with an ATS crawler has
"provenance" in the weak sense.

What nobody has — because it requires either a doctrine incumbents' revenue
forbids or longitudinal state aggregators don't keep — is **verified truth over
time**: when a posting first appeared, whether it's still there tonight,
whether the company's hiring is accelerating or decaying, what the posting
*explicitly refuses* (sponsorship no's), and — eventually — what happened to
people who applied. LinkedIn and Indeed structurally cannot copy this: their
payers are the employers whose stale and ghost ads the feature would expose.
Hiring Cafe *could* copy pieces, but has no curation stance, no
confirmed-vs-unconfirmed discipline, and employer-side incentives of its own
now.

---

## 4. Differentiation that survives contact

Five claims, each grounded in something already in the repo, each something a
leader structurally can't or won't match. "AI-native" appears in none of them
— every competitor says it and it selects for the S5 arms race.

1. **The no-ghost guarantee.** Every role was live on the company's own ATS at
   last night's build, and the page says when it was last checked and shows the
   first-seen date. Roles that vanish get struck through, not deleted
   (FINDINGS: "the fold is the only honest departure ledger"). LinkedIn can't
   do this — it would indict its own inventory. *Exists today; needs surfacing,
   not building.*

2. **Hiring momentum you can trust.** Per-company trend from the git-history
   time series (SPEC feature 13), computed only over genuinely observed
   snapshots — "this company added 12 engineering roles in 30 days" vs "this
   posting has sat for 94 days." No one else can publish this honestly because
   no one else records checked-vs-unchecked per night. *Data exists from
   ~2026-08-29 (T7.1, ~30 snapshots); the discipline already exists.*

3. **The openness register, including the no's.** The only index of what
   postings *explicitly say* about hiring from abroad — yes, no, and an honest
   "says nothing," never a guess. 1,891 stated-yes roles already rivals the
   hand-curated S2 market leader's annual volume. The explicit `no` is the
   feature no aggregator will build (it shrinks their clickable inventory) and
   the one that most respects a S2 seeker's week. *Exists at 10% coverage;
   extraction improvement is the highest-value build work (FINDINGS §2).*

4. **A curated universe, not an index.** 789 funded companies is not a small
   Hiring Cafe; it is a *vetted list* — the register knows why each company is
   in (funding rule fired, board verified against the company's own address,
   MCA/Companies-House identity badges) and says why others aren't
   ("unchecked," never "not hiring"). YC's Work at a Startup proves seekers
   value a bounded, vetted universe. Smallness is the product; stop apologizing
   for it. *Exists today; the weakness is the 2,093 unchecked — closing that is
   corpus work, not doctrine work.*

5. **The referral anchor (the business, not this quarter's build).** The
   register's honesty is the customer-acquisition and trust layer for the real
   product: getting a person referred via registered partners, where the unit
   is company + person, not a posting (FINDINGS: r03-c). refer.me proves
   demand; none of the referral marketplaces has a truth layer, and none of
   the truth layers has referrals. Holding both is the position. *Depends on
   partners that don't exist yet — see risks.*

---

## 5. What this means for the interface

The founder's complaint — *"do not think that this is just a board"* — decoded
by the segmentation: a board answers "what jobs exist?"; the product must
answer **"is this real, am I eligible, and how do I get in?"** The nine
variants perfected the first question's typography.

### The ten-second contract

Within ten seconds of load, a first-time S1 visitor must be able to **name a
company they want, and get back a verdict, not a list.** The interaction,
concretely:

1. **The page opens on one input, cursor already in it,** over a single line of
   proof-of-life: "27,689 roles · read from 789 companies' own boards · last
   night 20:00 UTC." Not a filter bank. Not a fold of 200 rows. One question:
   *"Which company? (or what role, where)"*

2. **Typing a company name resolves to a company verdict card** — the atomic
   unit of the product, and the thing to design next round:
   - the count: "OpenAI · 380 roles live on their own board as of Aug 4";
   - momentum: added / gone in the last 7 days (confirmed-new only — "a count
     it does not hold is a count this page will not invent");
   - the openness verdict: "12 roles state they sponsor · 3 state they don't ·
     365 say nothing";
   - the roles themselves, each line carrying first-seen date and its own
     apply URL onto the company's board;
   - and the door to the future: "Want a person, not a portal?" — the referral
     waitlist ask, which is finally something sign-in *buys* (FINDINGS §4:
     the gate measured nothing because yes bought nothing).

3. **A company we don't hold answers honestly and usefully.** Type "Figma":
   "Not in the register — we haven't verified Figma's board" plus the nearest
   verified companies. Never a silent empty result. With 2,093 of 2,925 corpus
   companies unchecked, this path is hit constantly; it is *the* place the
   doctrine ("we could not look" ≠ "nothing there") becomes visible product
   instead of a footnote. It is also the corpus-growth funnel: every miss is a
   vote for which board to verify next.

4. **Typing a role query instead** ("staff frontend Tokyo visa") cuts at the
   role and prints the yield line before asking to be believed (r02-b's
   pattern): "lights 14 · 3 state no · 209 say nothing and are exactly as
   bright as they were."

**The testable definition of done:** cold load → keystroke → a company verdict
card (or an honest miss) in under 10 seconds; and time-to-first-kept-role under
60 seconds for a S1 script ("find a live staff engineering role at a funded SF
startup, added this week"). An evaluator can run both against a stopwatch.

What this kills from the current design: the register-as-opening-view. The
6,423-row honest ledger becomes the *second* screen — the receipt behind the
verdict — not the front door. Nothing about the doctrine changes; what changes
is that the doctrine gets a question to answer.

---

## 6. The honest risks

1. **The verdict card needs corpus lookup breadth the build lacks.** 72% of
   the funding corpus is unchecked, and marquee names (Figma, Canva, Mistral,
   Revolut) are absent. The "honest miss" path mitigates the interface risk,
   but if most dream-company queries miss, the product feels empty regardless
   of honesty. *Dependency: corpus expansion — slug resolution and probe
   capacity, not design.*

2. **Momentum needs ~30 clean nightly snapshots — earliest 2026-08-29 (T7.1)
   — and the world rebuild just reset the definitional clock.** T15.2's own
   lesson: a widened radar manufactures phantom "new." First-seen on the
   789-company corpus starts confirming from the first nightly after the
   rebuild. Ship the badge only on confirmed sightings; expect skeptics to
   test it.

3. **The openness signal is a keyword heuristic at 10% coverage, unmeasured
   on non-English boards, with no translation** (SPEC v2 non-goals). S2 as a
   niche works at 1,891 roles; S2 as a marketed promise needs extraction
   recall the build has never measured. The bilingual occupation vocabulary
   (FINDINGS §3) is prerequisite for Japan/Korea credibility.

4. **No server-side user state exists.** Keeps, application records, the
   referral waitlist — all need the `PUT /keeps` Worker path (FINDINGS' #1
   ask) and the still-broken TLS hostname (or the ladder-step-4 hosting move).
   Until then, every "sign in buys X" claim in §5 is unbacked.

5. **No one has demonstrated paying for honesty.** Ghost-job pain is
   documented; payment for its absence is not — Hiring Cafe's free model may
   simply be the market's answer, which pushes revenue to the referral side
   and makes the register a free trust-builder. Plan revenue accordingly:
   seeker subscriptions are a bridge at best (S2's $15/mo precedent), the
   referral marketplace is the business.

6. **The referral marketplace has no partners, unresolved employer-ToS
   exposure (many employers forbid paid referrals), and payment/identity/tax
   machinery none of this repo touches.** refer.me proves demand, not
   legality-at-scale. The register can launch the *waitlist* this quarter to
   measure demand (that's what makes ladder step 3's gate finally measure
   something) — but nobody should mistake a waitlist for a marketplace.

7. **Description text at corpus scale (F1) does not exist**, so resume-to-role
   matching — the thing every "AI job search" competitor leads with — cannot
   be built this quarter. That's survivable (matching is commoditized; truth
   isn't) but it must be said: the near-term product wins on verification and
   entry, not on matching intelligence.

---

## 7. Next quarter, in one list

1. **Design round 4 aims at the company verdict card and the one-input
   opening** (§5) — the register becomes the receipt, not the door.
2. **Ship `PUT /keeps` + the referral waitlist** so sign-in buys something and
   the gate's counts become decision-grade (unblocks measurement for
   everything else).
3. **Corpus breadth:** burn down the 2,093 unchecked, prioritized by
   dream-company misses once the input ships.
4. **Openness extraction v2** — the highest-value build work per FINDINGS;
   it is what makes S2 a marketable segment instead of a niche shelf.
5. **Let the snapshots accrue** for momentum (T7.1, ~Aug 29) and ship the
   trend only over confirmed observations.
