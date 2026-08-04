# ROCKETSHIP — what the register can provably call a rocketship, and what it would take to mean it

*2026-08-04. Every corpus number below was recomputed from the world build
(`buildclone/data/companies.json`, snapshot 2026-08-04, schema 11) rather than
quoted. Every source claim was checked against the live source — YC's directory
and official API were fetched, six quarters of SEC Form D were downloaded and
parsed, TechCrunch's API was called. Pricing and licence terms are from
August-2026 retrieval, cited inline.*

## The verdict, up front

**The pitch says "recently funded by highly credible individuals, angels,
investors, VCs." The register can prove the *credible* half for 298 companies
and the *recently funded* half for 122, and it can prove *which investor* for
zero. But the missing data is not mostly missing from the world — it is missing
from `data/companies.json` because the pipeline fetches it and throws it away.**

Three measured facts drive everything below:

1. **YC's directory hands us `batch`, `team_size`, `status` and `top_company` on
   100% of the 298 YC companies, in the call `src/yc.py` already makes, and
   `yc.py` reads 4 fields out of 29 and discards the rest.** No new request, no
   new source, no licence question. This is the single largest provable gain
   available and it is a one-file change.
2. **SEC Form D cannot name investors — measured, not assumed.** The filings name
   directors, and across 2,814 related-person rows on 852 technology filings,
   exactly **10** name a fund in the clarification field. What Form D *can* state
   is the shape of the round, in fields the pipeline currently drops.
3. **The 369 companies that can say nothing about their funding are exactly the
   369 whose sources forbid us republishing them.** CB Insights (291) and Forbes
   (78) are the entire silent set. Cutting them removes the register's biggest
   honesty hole and its biggest legal exposure in one motion.

The claim that is fully provable this week, on real evidence, with a link behind
every word:

> **789 companies whose boards we read last night — 420 of them can tell you,
> from a source you can click, why they belong here.**

Not "recently funded by credible investors." That sentence is 15% true and the
part that is missing is the part the pitch leans on hardest.

---

## 1. What signals already exist, and what each actually proves

### 1.1 The register today

| Field | Present on | What it is |
|---|---|---|
| `source_url` | **789 / 789** | The citation backbone. Every row can link its evidence. |
| `qualified_by` | 789 / 789 | Which of three rules admitted it: `stage` 667 · `amount` 117 · `letter` 5 |
| `amount` | 122 / 789 | Median **$30M**, min $5M, max $4.08B. All ≥ $5M — the corpus's own floor. |
| `date` | 122 / 789 | 2026 × 26 · 2025 × 93 · 2024 × 2 · 2020 × 1 |
| `round_letter` | **5 / 789** | A × 4, B × 1. Effectively nothing. |
| **investor names** | **0 / 789** | **The field does not exist.** `src/record.py`'s `Record` TypedDict has eight keys and none of them is an investor. |

Source provenance, and what each source's rule was:

| Source | Companies | Roles | Qualified by | What the source actually states |
|---|---|---|---|---|
| YC directory | 298 | 7,744 | `stage` | YC funded it; YC calls it `Growth` |
| CB Insights | 291 | — | `stage` | Valued ≥ $1B at some point |
| SEC EDGAR | 101 | — | `amount` | A Form D reporting ≥ $5M sold |
| Forbes | 78 | — | `stage` | On AI 50 / Cloud 100 / Fintech 50 / Next Billion-Dollar |
| TechCrunch | 20 | — | `amount` 16 · `letter` 4 | A headline announcing a round |
| FinSMEs | 1 | — | `letter` | A wire item |

### 1.2 What each signal can and cannot support

**YC / accelerator membership — a real credibility signal, and the strongest one
we hold.** 298 companies, 7,744 roles (28% of the register). This is the one
place the pitch's "highly credible investors" is literally true and nameable:
Y Combinator is the investor, YC says so on its own page, and `source_url`
already points at it. It proves *who backed them*. It proves nothing about
recency — YC's own note is right that a batch date is not a funding date — and
nothing about what they raised since.

**CB Insights unicorn membership — proves size, and size is the opposite of the
thesis.** A $1B valuation says the rocket already launched. For a job seeker
hunting "the next rocketship," Stripe and Databricks are the control group, not
the answer. The source also states no amount, no letter, and no round date by
construction: `src/cbinsights.py` correctly refuses to read the "Date Joined"
column as a round date. So these 291 companies contribute a valuation claim the
register never renders and a funding claim it cannot make.

**Forbes list membership — editorial judgement, honestly recorded, weakly
probative.** 78 companies. `src/forbes.py` is scrupulous: it refuses to put
Forbes' lifetime funding total into `amount` because a lifetime total is not a
round, and it correctly gives Midjourney and Zoho no stage at all. The result is
that a Forbes row proves "an editor put this on a list," which is a real signal
and not a funding fact.

**SEC EDGAR Form D — the only source that files rather than reports, and the
most under-used thing in the repo.** 101 companies qualified this way. Form D is
a legal filing by the company's own counsel; `TOTALAMOUNTSOLD` is money in the
door, and `src/edgar.py` is right to prefer it over the open-ended
`TOTALOFFERINGAMOUNT`. It is public domain, free, one call per quarter, and
carries zero licensing risk.

**What Form D does *not* give: investors.** I tested this directly rather than
assuming. The 2026Q1 dataset has six tables; `edgar.py` opens two.
`RELATEDPERSONS.tsv` is the largest table in the zip (8.2 MB, 53,159 rows) and is
never read. Joined to the 852 technology operating companies:

- 852 / 852 filings have at least one related person; 2,814 person rows total
- Relationships: **Director 2,317 · Executive Officer 1,540 · Promoter 201**
- 755 filings name at least one Director
- **Clarification text naming a fund-like entity: 10 of 2,814.**

So Form D names *people* — and a startup's outside directors are usually its VC
partners. But turning "Director: Sarah Guo" into "funded by Conviction" is an
inference from an external mapping the filing does not contain. Under this
repo's doctrine that is precisely the move that is forbidden: it would render a
guess in the same ink as a filed fact. **Form D is not a path to investor names,
and anyone who tells you otherwise has not opened the table.**

### 1.3 Data the pipeline fetches and discards

This is the section that changes what can ship this week.

**`src/yc.py` reads 4 fields of 29.** The mirror it calls
(`yc-oss.github.io/api/companies/all.json`, one GET, 6,119 companies) returns:

| Field | Coverage on our 298 | Currently read? |
|---|---|---|
| `batch` (e.g. "Winter 2021") | **298 / 298** | no |
| `status` (Active / Acquired / Public / Inactive) | **298 / 298** | no |
| `team_size` | **294 / 298** (median 70) | no |
| `top_company` (YC's own designation) | **36 are true** | no |
| `tags`, `industries`, `regions`, `one_liner`, `launched_at` | 100% | no |
| `name`, `url`, `stage`, `website` | 100% | **yes** |

The 298 companies break down by batch year 2007 → 2025. Recent cohorts:
**batch 2021 or later = 110 companies / 1,570 roles**; 2019+ = 160 / 2,423;
2016+ = 228 / 4,792. And `status` is not decoration: **33 of the 298 are
Acquired, Public or Inactive** — companies a "next rocketship" register arguably
should not carry, and currently cannot tell apart.

**`src/edgar.py` reads 5 of `OFFERING`'s 41 columns and 3 of `ISSUERS`' 23.**
Measured on 852 technology filings in 2026Q1, the discarded fields include:

| Discarded field | Stated on | Why it matters |
|---|---|---|
| `TOTALNUMBERALREADYINVESTED` | **852 / 852** | Median 4, p90 28, max 362. Four investors is an institutional round; 362 is a retail syndicate. |
| `YEAROFINC_VALUE_ENTERED` | 609 / 852 | Founding year → company age at raise |
| `TOTALOFFERINGAMOUNT` | 778 / 852 | The ceiling, next to the amount sold |
| `MINIMUMINVESTMENTACCEPTED` | 286 / 852 | A $1M minimum is institutional; $5k is not |
| `REVENUERANGE` | 193 / 852 | Actual revenue bracket (656 decline to disclose) |
| `SALESCOMM_DOLLARAMOUNT` > 0 | 25 / 852 | **A negative signal.** Top-tier VC rounds pay no sales commission. |
| `FINDERSFEE_DOLLARAMOUNT` > 0 | 7 / 852 | Same |
| `RECIPIENTS` (broker/placement agent) | 49 / 852 | Same — a placed round, not a led round |
| `FEDERALEXEMPTIONS` = `06c` | 37 / 852 | General solicitation — advertised to accredited retail, not a VC round |
| `JURISDICTIONOFINC` / `ENTITYTYPE` | 682 Delaware / 777 Corporation | The Delaware C-corp is the standard VC structure |
| `ISSUERS.CITY` | 852 / 852 | HQ, free |

That is the raw material for a *shape-of-round* test that never guesses an
investor. More on it in §2.

**`src/techcrunch.py` asks the API for `_fields=title,link,date` and never
requests the body.** Investor names live in the prose ("closed a $50 million
Series C round **led by Insight Partners**"). I checked 12 live venture posts:
the `excerpt` field names an investor in roughly 2. The full `content` would do
much better. But TechCrunch supplies **20 of 789 companies**, so even a perfect
extractor moves 2.5% of the register. Worth doing; not worth prioritising.

**`stage` never reaches the site.** `corpus.json` carries `stage` on 1,881 of
2,925 companies, `build.py:780-785` copies six funding fields into the row and
`stage` is not among them. So 667 rows can print `qualified_by: "stage"` and
cannot print *what the stage was*. The page can say "it qualified on a stage
label" and not "YC calls this company Growth." That is a citation with its
subject removed.

---

## 2. A rocketship score that is defensible

### 2.1 The rule that makes it auditable

**No composite number. No 0–100. No weights.** A score that blends five signals
into one integer cannot be cited, because there is no source URL for "73." The
moment a reader asks "why 73?", the honest answer is "because we picked those
weights," and the register has spent its credibility.

Instead: **a rocketship is a company that lights a set of independently
citable badges, and the page shows the badges, not their sum.** Each badge names
its source, states its date, and links its evidence. Sorting can rank on badge
count; the *display* never collapses them.

### 2.2 The badges that hold today

Every one of these is computable from data already on disk or already fetched,
and each renders as a sentence with a link.

**① Backed by a named accelerator — 298 companies, 7,744 roles.**
> *Y Combinator, Winter 2021 · [ycombinator.com/companies/…]*

The only badge in the set that names an investor. Costs one field read.

**② Recent cohort — 110 companies (batch 2021+), 1,570 roles.**
Batch year is stated by YC and is a date. This is not a funding date and must
never be labelled one; it is "how recently this company started."

**③ Still independent — 265 of 298 Active.**
`status` from YC. The negative case matters more: 16 Acquired, 14 Public, 3
Inactive. A register of rocketships that lists an acquired company without
saying so is misleading its reader about the job.

**④ YC's own top designation — 36 companies, 2,951 roles.**
`top_company` is YC's editorial call, not ours. Rendered as YC's claim, cited to
YC, it is honest; rendered as our judgement it is not.

**⑤ Filed a round — 122 companies, 3,729 roles.**
> *SEC Form D, filed 2026-01-28: $12,000,000 sold, 4 investors · [sec.gov/…]*

Recency buckets, measured: **≤12 months → 72 companies / 2,422 roles**;
≤18 months → 119 / 3,675. **Two rows are stale and must be excluded or labelled:
COLAB SOFTWARE (2024-04-30) and Tomo Networks (2020-08-24).** A register that
files a 2020 round under "recently funded" has broken its own promise on row one.

**⑥ Institutional round shape — computable on the EDGAR rows, no investor named.**
A filed round is institutional-shaped when it is a Delaware corporation, filed
under 506(b) rather than 506(c), reports no sales commission and no finder's fee,
has no broker-dealer recipient, and reports a small investor count. Each clause
is a filed field with a link. This does not say *who* invested. It says *this
round has the shape a led venture round has and not the shape a brokered retail
placement has* — and every clause of it is auditable against the filing.

**⑦ Hiring intensity — open roles ÷ headcount. 294 YC companies have both
numbers today.** This is the strongest "bet to become a rocketship" signal
available this week, and it needs no snapshots:

| Company | Open roles / staff |
|---|---|
| Finni Health | 111 / 40 = 2.77× |
| Inversion Space | 68 / 28 = 2.43× |
| Replit | 90 / 65 = 1.38× |
| Oklo | 64 / 50 = 1.28× |

217 companies have ≥10 staff and ≥5 open roles. Rendered honestly it is two
stated numbers side by side and no arithmetic claim: *"YC's directory lists 65
people · their own board shows 90 open roles today."* Both cited, neither
invented. The caveat that must ship with it: `team_size` is self-reported to YC
and can be stale, so the badge states the source, never asserts headcount.

### 2.3 The signals to reject, and why

**Round letter — dead.** 5 of 789. Four A's and one B. There is no version of
"seed / A / B / C / pre-IPO" that this corpus can filter on. Do not build the
filter; do not put the words in the UI.

**Round size relative to stage — not computable.** It needs a stage, and stage
is a binary `growth`/absent that does not reach the site. A $30M round is a big
A and a small C, and the register cannot tell which.

**Investor quality — not obtainable at any price the product can pay.** See §3.
There is no free or cheap source of investor names that may lawfully be
displayed on a public page.

**Hiring velocity over time — real, and roughly four weeks away.**
`first-seen.json` on the world build holds **7 dated URLs** and 371 companies
observed on both of the last two nights. The world rebuild reset the clock, as
STRATEGY §6 warns. Headcount growth and role-mix shifts ("first sales hire")
need ~30 clean snapshots. Build the badge; do not ship it until the snapshots
exist, and ship it only over confirmed observations.

**Role-mix as a static signal — available now, weakly probative.** Department is
known on 27,482 of 27,689 roles. "12 of their 30 open roles are Sales" is a real
observation about a company's stage. It is not evidence of funding and should
not be dressed as it.

---

## 3. Data acquisition, ranked by value per unit of effort

### Tier 1 — free, already fetched, ship this week

**1. Read the rest of YC's payload.** `batch`, `status`, `team_size`,
`top_company` on 298 companies. Zero new network calls, zero cost, zero licence
question. Unblocks badges ①②③④⑦. **This is the highest-value change in the
document and it is a one-file diff.**

One caveat to fix while you are in there: `yc-oss` is **unofficial and declares
no licence at all** — it scrapes YC's Algolia index via daily GitHub Actions. The
official API (`api.ycombinator.com/v0.1/companies`) I fetched and confirmed
returns `batch`, `teamSize`, `status`, `badges`, `tags`, `regions` and
`locations`. It omits `stage` — which is why `yc.py` chose the mirror — but if
`batch` becomes the qualifying signal, `stage` stops mattering and the official
API becomes strictly the safer dependency. Cost: 244 paged calls once a night.

**2. Carry `stage` through to `companies.json`.** One line in `build.py`. Lets
667 rows say what qualified them instead of only that something did.

**3. Read the Form D fields already in the downloaded zip.** Investor count,
year of incorporation, exemption type, commission/finder's fee, broker
recipients, jurisdiction. Zero new calls — the zip is already on disk. Unblocks
badge ⑥.

### Tier 2 — free, small build

**4. Widen the EDGAR industry filter and match by name, not just by admission.**
I ran this: matching all 789 company names against six quarters of Form D (all
industry groups, non-fund, non-amendment) finds **132 matches**, of which **13
match only outside the current `Computers / Other Technology /
Telecommunications` filter** — MoonPay files under "Other Banking and Financial
Services," Curative under "Health Insurance." Doing this would take dated rows
from 122 to **~151 of 789 (19%)**.

**Be clear about the ceiling: 657 of 789 have no Form D at all.** They are
foreign issuers with no filing obligation, or they raised more than 18 months
ago, or they are late-stage. **Parsing EDGAR harder does not solve the 667.** It
is worth the afternoon it costs, and it is not the answer.

A second caveat found while testing: Form D's `TOTALAMOUNTSOLD` is frequently
*not* the headline round. Lob's most recent filing reports $200,000 and Render's
$500,000 — option-pool top-ups and partial closes, not rounds. The ≥$5M floor
already filters these out of qualification, but any UI that renders the number
must render it as *what the filing says*, never as "raised."

**5. Fetch TechCrunch article bodies for investor names.** Add `excerpt` or
`content` to the existing `_fields` parameter — same 10 calls. Reaches 20
companies. The facts (company, amount, investor, date) are facts and extracting
them is defensible; republishing TechCrunch's prose is not. Low value, low cost,
do it last.

### Tier 3 — paid, and mostly unusable

| Option | 2026 price | Can it be displayed on a public page? |
|---|---|---|
| **Crunchbase Basic / Pro** | $49 / $99 per month | **No.** Full API needs an Enterprise or Applications licence. |
| **Crunchbase Enterprise** | **$50,000+/yr** | Only as permitted in the Order Form |
| **PitchBook** | **$12k–$30k+/yr per seat**; typical single seat ~$20k | Seat licence, not a data feed |
| **Harmonic.ai** | **~$25k/yr**, no public rate card | Unstated; sales-gated |
| **Crustdata** | from $49/mo, free tier | Redistribution terms not published |

**The licence, not the price, is the blocker.** Crunchbase's Data Access Terms
state that a licensee *"may not license, sublicense, sell, offer to sell,
distribute or otherwise provide any Crunchbase data to any third parties,"* with
one exception: *"Licensee may publish, share, and distribute analysis and
aggregate statistics derived from the Crunchbase data."*

A public job register that prints "Acme · Series B · $40M · March 2026 · led by
Accel" for each company is **displaying per-entity Crunchbase data to third
parties**. That is the prohibited use. Aggregate statistics are permitted — "the
median round in our register is $30M" is fine — but the founder's product is
per-company by definition. **A $99/month Crunchbase Pro seat is a research tool
for a human, not a feed for this page.** Buying it and rendering it would put the
product in breach on day one, and it would do so on the single page the whole
pitch rests on.

### The legal exposure that already exists

Two of the six live sources are being used in ways their operators forbid, and
they are **47% of the register**:

- **CB Insights (291 companies).** Their Terms of Use prohibit *"any robot,
  spider or other automatic device, process or means to access the Website for
  any purpose, including monitoring or copying any of the material,"* and
  separately prohibit manual copying without written consent. `src/cbinsights.py`
  does exactly the first. Their `robots.txt` does not block
  `/research-unicorn-companies` for `User-agent: *` — but it does block `GPTBot`
  from `/company/`, which is the URL pattern used as `source_url` on all 291
  rows. **robots.txt is not a licence**, and the ToS is the operative document.
- **Forbes (78 companies).** `src/forbes.py` calls `forbes.com/forbesapi/…`, an
  internal endpoint the page uses for itself and Forbes does not publish for
  third parties.

By contrast **SEC EDGAR is public domain and free**, with a declared user agent
and a rate limit as the only conditions — which `edgar.py` already respects.
That asymmetry should decide where the next engineering hour goes.

### The one source worth buying or building first

**Neither: read YC's payload.** It is free, it is already in the nightly, it
names an investor the reader has heard of, it covers 298 companies and 28% of
roles, and it is the only badge in §2 that makes the pitch's own sentence true.
Every paid option costs $20k–$50k/yr, and the two cheapest forbid the exact
display the product needs.

If a budget appears later and the register has proven demand, the question to
ask a vendor is not "how much?" but **"put in writing that we may display
per-company funding facts on a public page."** If they will not, the price is
irrelevant.

---

## 4. The honest interim — what ships this week

### The numbers

| Claim | Companies | Roles | Provable? |
|---|---|---|---|
| Y Combinator batch, named and dated | **298** | 7,744 (28%) | yes, one field read |
| Filed round, ≤ 18 months | **119** | 3,675 (13%) | yes, today |
| Filed round, ≤ 12 months | 72 | 2,422 (9%) | yes, today |
| **Either — the register's evidenced half** | **420 of 789 (53%)** | ~11,400 | yes |
| **Neither — cannot state anything about funding** | **369 (47%)** | **16,216 (59%)** | no |

The two sets are **disjoint**: not one of the 298 YC companies has a round date,
and not one of the 122 dated companies is a YC company. So the badges compose
cleanly and the union is a straight sum.

**The 369 silent companies are 291 CB Insights + 78 Forbes — all of them, exactly.**

### The framing

The strongest honest sentence available this week is not about funding. It is
about *evidence*:

> **789 companies, read from their own boards last night. 420 of them can show
> you why they're here — a Y Combinator batch or a funding round they filed with
> the SEC. The other 369 got in on a valuation or a magazine list, and we say
> which.**

The register renders three states, never two: **backed** (YC, named and dated),
**filed** (SEC Form D, dated and linked), and **listed** (CB Insights / Forbes —
in the register on a third party's judgement, with no funding fact behind it).
That third label is the doctrine working. It is also, read plainly, an argument
for §5.

**What must not be said this week:** "recently funded by credible investors"
(true for 15%, and never with a named investor); anything using the words seed,
Series A/B/C or pre-IPO (5 letters in 789 rows); any composite score.

---

## 5. What to cut

**Cut the round-letter universe. Now, and say it out loud.** "Seed, Series A, B,
C, pre-IPO" cannot be evidenced this quarter or next. The corpus holds five
letters. There is no free source of letters, and the paid ones forbid displaying
them. Every hour spent on a stage filter is an hour spent building a control
that will render five rows. **Delete it from the pitch, the roadmap and the UI.**

**Cut "credible individuals and angels" entirely.** Individual angel names are
not in any source the product can lawfully display. Form D names directors, not
backers, and the one legitimate reading of it — outside directors are usually
investors — requires a mapping that no filing contains. This is the part of the
founder's stated universe with no path at all, at any budget under $50k, and it
should be struck rather than deferred.

**Retire the CB Insights source, and reconsider Forbes.** This is one decision
that fixes three problems at once:

1. **They are the entire silent 47%** — 369 companies, 16,216 roles that can
   state nothing about their funding.
2. **They are the entire legal exposure** — the only two sources used against
   their operators' stated terms.
3. **A unicorn is the opposite of the thesis.** CB Insights' list is companies
   already valued at $1B. The founder is hunting *the next* rocketship. Stripe
   and Databricks are not it — they are the outcome the register is supposed to
   help someone catch early.

The cost is real and should be stated plainly: dropping both takes the register
from 789 companies to 420, and from 27,689 roles to roughly 11,400. **That is
the price of every remaining row being able to answer "why is this company
here?" with a link.** STRATEGY §4 already argues that smallness is the product
and the register should stop apologising for it; this is where that argument
gets tested with a real number.

If 420 is too small to launch, the honest alternative is to **keep them and
label them** — the `listed` state in §4 — and never to keep them and let the
homepage headline imply they were funded. What is not available is keeping 789
companies *and* the sentence "recently funded by credible investors."

**Keep and reframe: "recently funded" → "recently backed, and here's by whom."**
The founder's instinct is right; the noun is wrong. The register cannot prove a
recent *round* for most companies. It can prove a named *backer* for 298 — and
"Y Combinator, Winter 2021" is a more credible sentence to a job seeker than "$40M
Series B" from an unnamed source anyway. **The moat the founder named — "the
representation and solving the problem with ease" — survives this cut intact.
The register does not need more data to represent well. It needs to render the
data it already downloads.**

---

## 6. Do this, in order

1. **Read YC's remaining fields** (`batch`, `status`, `team_size`,
   `top_company`) into `companies.json`. One file. Unblocks five of seven badges.
   Move to the official API while you are there — `yc-oss` has no licence.
2. **Carry `stage` through `build.py`** so 667 rows can name what admitted them.
3. **Ship the three-state register** — backed / filed / listed — with the badge
   set in §2.2 and no composite score.
4. **Exclude or label the two stale rounds** (Tomo Networks 2020, COLAB 2024)
   before anything says "recently."
5. **Read the Form D fields already on disk** (investor count, exemption,
   commission, jurisdiction) for badge ⑥.
6. **Widen the EDGAR match** — 122 → ~151 dated rows, one afternoon.
7. **Decide on CB Insights and Forbes.** Not an engineering task. A founder's
   call about what the register is for, and it gates the headline.
8. **Let the snapshots accrue** for hiring velocity; ship it only over confirmed
   observations, no earlier than ~2026-08-29.

---

## Sources

- [Crunchbase Data Access Terms](https://data.crunchbase.com/docs/terms) · [Crunchbase License Agreement](https://data.crunchbase.com/docs/license-agreement) · [Crunchbase API pricing 2026](https://nubela.co/blog/crunchbase-api/) · [free tier removal](https://dev.to/agenthustler/crunchbase-api-in-2026-free-tier-gone-what-startup-data-hunters-do-now-1177)
- [PitchBook pricing 2026](https://easyvc.ai/vs/pitchbook-pricing/) · [PitchBook buyer pricing](https://costbench.com/software/financial-data-terminals/pitchbook/)
- [Harmonic.ai pricing](https://prospeo.io/s/harmonic-pricing-reviews-pros-and-cons) · [Crustdata pricing](https://crustdata.com/pricing)
- [CB Insights Terms of Use](https://www.cbinsights.com/website-terms-of-use) · `cbinsights.com/robots.txt` (retrieved 2026-08-04)
- [yc-oss/api](https://github.com/yc-oss/api) — unofficial, no licence declared · `api.ycombinator.com/v0.1/companies` (fetched 2026-08-04)
- SEC Form D quarterly data sets, `2024q4`–`2026q1` (downloaded and parsed 2026-08-04); `2026q2` returns 404 — not yet published
