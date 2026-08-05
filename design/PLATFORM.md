# PLATFORM — where the agentic product runs, and what v1 must not foreclose

*2026-08-05. Cloudflare account state was re-verified live against the API this
session, not quoted from `HANDOFF.md`. Vendor pricing is from vendor
documentation fetched today and is cited inline. Every cost figure below is
either **measured** (a rate published by the vendor), **derived** (arithmetic
over a stated token model), or **estimated** (a usage assumption I am guessing
at) — each is labelled, because a number that moves on a definitional choice is
not a measurement.*

---

## Executive summary

**Infrastructure is not the decision. The model bill is.** At 10,000 users each
running the flagship feature — a hundred applications a month — the whole
Cloudflare footprint costs roughly **$2,400/month** and the Claude tokens cost
roughly **$210,000/month**. Infrastructure is ~1% of variable cost. Choosing a
platform to save money is optimising the wrong 1%. Choose on what is already
built, already paid for, and already provisioned — and that is Cloudflare.

**Stay on Cloudflare.** The Worker with Clerk auth, D1 and R2 exists and is
deployed; the account, the zone, and the bindings all verified live today. Every
capability problems 3–7 need has a first-party Cloudflare product that is GA as
of Agents Week 2026: Workflows (durable execution), Browser Run (form
automation), Sandboxes, Agent Memory, MCP. Email Service is public beta and the
Agents SDK is preview — those two are the only soft spots, and neither is on
v1's path. Vercel's stack (eve, Sandbox, Workflow DevKit) is genuinely good and
costs about the same; it buys nothing that justifies abandoning a working,
provisioned Cloudflare install. **Anthropic Managed Agents is not a competing
host — it is a runtime you can call from a Worker, at $0.08 per active
session-hour plus tokens, and the tokens dwarf the session fee.**

**The finding that should change the roadmap:** problem 3 ("fill application
forms for me") cannot be one product, and the repo already measured why.
`worker/questions.mjs` records that **Greenhouse publishes a posting's questions
and Ashby and Lever publish nothing — 401 of 880 resolved slugs are Ashby.**
And Greenhouse's own API docs show the sanctioned submission endpoint
(`POST /v1/boards/{board_token}/jobs/{id}`) authenticates with **the employer's
board API key, not the applicant's**. So the sanctioned auto-apply path runs
through registered employer partners — the same shape the founder already chose
for referrals — and browser automation is the unsanctioned path for everyone
else. The doctrine already written into SPEC v4 ("nothing auto-submitted") turns
out to be simultaneously the ToS-safe path, the cheap path, and the brand.
That convergence is the strongest strategic fact in this document.

**The cost wall, stated once:** at Sonnet 5 rates, one weekend of "apply to 100
companies" costs **~$21 of tokens per user** (derived, §2). A job seeker's
demonstrated willingness to pay is $15–30/**month** (`STRATEGY.md` §2). **One
weekend of the flagship feature costs more than a month of subscription.** The
flagship feature must be metered from the first line of code, or it is a
business that loses money faster the better it works.

**What to decide now**, before feature 1 ships this week:

1. **Serve the site from the Worker, on the two-level hostname.** Re-measured
   today: `api.roleatlas.sennamind.com` still fails TLS handshake, and
   `roleatlas.sennamind.com` returns 200. Ladder step 4 deletes that problem
   rather than fixing it.
2. **Key all state on the company, not the posting** — `PRODUCT-1.md` §5 already
   argues this from the product side; the referral endgame makes it structural.
3. **Keep every model call behind one `llm.mjs` seam** and every corpus query
   behind one tool-function module. That is the whole portability rule (§6).

**What to defer, deliberately:** the agent runtime (Agents SDK vs Workflows vs
Managed Agents), Browser Run entirely, email ingestion entirely, and the MCP
server. None of them is needed for problems 1 or 2, and every one of them is a
week's work *after* the seams in §6 exist — versus a rewrite without them.

**The one thing worth building earlier than it looks:** the corpus as an **MCP
server** (§5.4). It is a few hundred lines on a platform that has first-class
support for it, its marginal cost is approximately zero, and it is **the only
item in the roadmap whose unit economics improve with scale** — because the
calling agent's owner pays for the inference, not us.

---

## 1. What actually exists (verified live, 2026-08-05)

Everything in this section was checked against the Cloudflare API this session
rather than read out of `HANDOFF.md`.

| Thing | State | How checked |
|---|---|---|
| API token | **active**, `not_before` 2026-08-02, **expires 2027-01-31** | `GET /user/tokens/verify` |
| Worker `roleatlas-api` | deployed, modified 2026-08-03 | `GET /accounts/{id}/workers/scripts` |
| D1 `roleatlas` | exists, `8383daaf-…` | `GET /accounts/{id}/d1/database` |
| R2 `roleatlas-resumes` | exists | `GET /accounts/{id}/r2/buckets` |
| `roleatlas.sennamind.com` | **HTTP 200** | `curl` |
| `api.roleatlas.sennamind.com` | **`sslv3 alert handshake failure`** | `curl` |

Two corrections to `HANDOFF.md` worth carrying forward:

- The token's TTL is not vague — **it expires 2027-01-31**. Nothing in this
  document is blocked by credential expiry within the planning horizon.
- The TLS failure is not an hour old, it is **a day old**. HANDOFF's leading
  theory (a three-level hostname that Universal SSL's `sennamind.com` +
  `*.sennamind.com` coverage cannot reach) now has 24 hours of evidence behind
  it rather than one. Treat it as confirmed unless a dashboard check says
  otherwise. **It is a reason to make the hosting decision, not a bug to fix.**

Two measured constraints from the repo itself, which drive §5.3 more than any
vendor's pricing page does:

- **`worker/questions.mjs`** (measured 2026-08-02): Greenhouse states a job's
  application questions on request; **Ashby and Lever state nothing**, and
  **401 of 880 resolved slugs are Ashby**. Roughly half the register cannot be
  read, let alone auto-filled, through any API.
- **The billing finding** (measured 2026-08-02): the Claude subscription cannot
  serve API traffic — `messages.create` 429s, Managed Agents 403s on scope.
  `describe.py` works only because it drives Claude Code agents. **Everything in
  §2 assumes a funded API account that does not yet exist.** That is a purchase
  decision, and it is the gate on problems 4–7.

---

## 2. The cost geometry, derived

This is the section the platform choice actually turns on, so the arithmetic is
laid out to be checked rather than believed.

### 2.1 The token model (stated assumptions — this is the definitional choice)

| Work | Input | Output |
|---|---|---|
| Tailor résumé + cover letter + "why this company", one pass | 6k | 3k |
| Agentic form fill (≈10 turns, DOM/screenshots, with caching) | 40k cache-read + 15k fresh | 6k |

Rates from the Claude API pricing table (Opus 5 $5/$25 per MTok; Sonnet 5 $3/$15
standard, $2/$10 introductory through 2026-08-31; Haiku 4.5 $1/$5; cache reads
~0.1×; Batch API 50% off).

### 2.2 Cost per application (derived)

| Model | Generation | Form fill | **Per application** | **× 100 (one weekend)** |
|---|---|---|---|---|
| Haiku 4.5 | $0.021 | $0.049 | **$0.07** | **$7** |
| Sonnet 5 | $0.063 | $0.147 | **$0.21** | **$21** |
| Opus 5 | $0.105 | $0.245 | **$0.35** | **$35** |

Routing the generation half through the Batch API (it is not latency-sensitive;
the user is asleep) takes Sonnet 5's hundred applications from $21 to **~$18**.
That is the single largest cost lever available and it costs one code path.

**The wall, in one line: $21 of tokens for a weekend, against $15–30/month of
demonstrated willingness to pay.** Haiku 4.5 at $7 is the only tier that fits a
subscription — and form-filling is precisely where a cheap model's mistakes are
unrecoverable, because a wrong answer submitted on someone's behalf cannot be
withdrawn. **Do not let the cost pressure choose the model for the one step
that writes to the outside world.** Cheap model for extraction and
classification; expensive model for anything a human will be judged on.

### 2.3 Infrastructure, same scale (derived from vendor rates)

10,000 users × 100 applications/month = 1M applications/month.

| Line | Rate (measured) | Monthly at 10k users |
|---|---|---|
| Workers Paid | $5 flat | $5 |
| Static assets (feature 1) | **free and unlimited** | $0 |
| Workers requests | 10M included | $0 (within) |
| Workflows steps (~6/application) | 500k included, $0.80/100k | ~$44 |
| Browser Run (90s/application) | 10 h included, **$0.09/h** | ~$2,250 |
| Durable Objects duration | 400k GB-s included, $12.50/M | ~$89 |
| Durable Objects requests | 1M included, $0.15/M | ~$3 |
| R2 (10k résumés ≈ 2 GB) | 10 GB free | $0 |
| Email Routing (inbound) | free on all plans | $0 |
| Email Sending | 3k/mo free, then $0.09/1k | ~$18 |
| **Total infrastructure** | | **≈ $2,400** |
| **Total Claude tokens (Sonnet 5)** | | **≈ $210,000** |

**Infrastructure is 1.1% of variable cost. The ratio is about 90:1.** Every
platform argument that turns on hosting price is arguing about the 1%.

Three things that are *not* costs but are real constraints at that scale:

- **Browser Run concurrency caps at 120 per account** (paid plan; docs say
  scalable on request). Average demand at 10k users is ~35 concurrent, but
  weekend-shaped load is 5–10× the mean — so **queue the fills and ask for a
  raise before you need it.** The binding constraint is concurrency, not dollars.
- **D1's free tier is 100k writes/day.** 1M applications/month at two writes
  each is ~67k/day — inside the tier, but not comfortably. Application records
  belong in Durable Object SQLite, not D1, before that becomes a 3am problem.
- **The R2 free-tier guard already in `resume.mjs`** (9 GB of 10, 800k of 1M
  Class A) is correctly sized for 10k users and starts refusing at roughly
  45,000. Raising it is the business decision `HANDOFF.md` says it is.

### 2.4 Vercel, priced on the same workload

Vercel Sandbox: $0.128/active CPU-hour, $0.0106/GB-hr memory, $0.15/GB network,
$0.60 per million sandbox creations; Hobby includes 5 CPU-hours. A 90-second
form fill at 1 vCPU / 2 GB is ~$0.0037, so 1M applications ≈ **$3,700/month**
against Cloudflare's ~$2,250. **Same order of magnitude, Cloudflare slightly
cheaper, neither material against $210k of tokens.** There is no cost case for
switching in either direction. §5 argues the decision on other grounds.

---

## 3. Per-problem mapping

Costs are **marginal** — the model tokens and the metered infrastructure only,
excluding the flat $5 Workers Paid plan. "1 user" is the founder using it for one
weekend; 100 and 10k are monthly, at 100 applications each, on Sonnet 5.

| # | Problem | Where it runs | What it needs | 1 user | 100 | 10k |
|---|---|---|---|---|---|---|
| **1** | Find the next rocketship | **Workers static assets** + sharded JSON | Nothing new. Already decided. | **$0** | **$0** | **$0** |
| **2** | Track what I applied to | **Existing Worker** + D1 + R2 + Clerk | `PUT /keeps`; TLS or the hosting move | **$0** | ~$0 | ~$90 |
| **3** | Fill application forms | **Split — see §5.3.** Partner API path: Worker + Workflows. Assist path: Browser Run + Workflow | Employer board keys (partner path); Browser Run + human submit (assist path) | $15 | $1,500 | $150,000 |
| **4** | Tailor résumé per role | Workflow step, **Batch API** | Funded API account; job-description text the corpus does not store | $3 | $300 | $30,000 |
| **5** | Cover letter variants | Same Workflow, same batch | Same | $2 | $200 | $20,000 |
| **6** | "Why this company" | Same Workflow; reads `description` the corpus already has | Same | $1 | $100 | $10,000 |
| **7** | Referrals, cold email, inbox watching | **Email Routing (inbound, free)** → Queue → Worker; Haiku 4.5 classifier; Agent Memory or DO for thread state | Registered partners; a sending domain; **inbox access, which is the hardest consent problem in the roadmap** | $2 | $200 | ~$20,000 |

Four notes the table cannot hold:

- **Problems 4–6 share one Workflow and one model call.** Tailoring a résumé,
  writing the letter, and answering "why this company" read the same inputs and
  should not be three round trips. Built together they cost roughly what one of
  them costs built separately.
- **Problem 4 has a data dependency nothing else has.** `STRATEGY.md` §1 records
  that job-description text is **not stored** — it is fetched per posting on
  demand. Résumé tailoring needs that text. Either the fetch happens inside the
  Workflow step (cheap, one extra hop, and it is what Browser Run is for anyway)
  or the corpus grows a column. That is a build decision, not a platform one,
  and it is the reason problem 4 is not as close as it looks.
- **Problem 7's cost is dominated by how you listen, not by what you think.**
  Polling a mailbox and classifying everything costs ~$1.80/user/month of Haiku
  tokens; receiving pushed mail through Email Routing and classifying only what
  arrives costs a fraction of that. **Push beats poll, and on Cloudflare push is
  free.** That is the one place the platform choice genuinely changes the bill.
- **Problem 1 is free at every scale**, because static asset requests are free
  and unlimited on Workers. The thing shipping this week has no marginal cost
  and never will. That is worth knowing before anyone optimises it.

---

## 4. The four options, assessed

### 4.1 Cloudflare all-in — **recommended**

What is actually GA after Agents Week 2026, which matters more than what exists:

| Capability | Status | Relevance |
|---|---|---|
| Workers + static assets | GA | Feature 1, already decided |
| D1 / R2 / Durable Objects | GA (DO SQLite billing began Jan 2026) | Problem 2, already built |
| **Workflows** (durable execution) | **GA**, control plane re-architected 2026 for higher concurrency | The spine of problems 3–6 |
| **Browser Run** (was Browser Rendering, renamed 2026-04-15) | **GA**; Puppeteer + Playwright, CDP access, Live View, human-in-the-loop, session recording | Problem 3's assist path |
| **Sandboxes** | **GA** | Only if untrusted code execution is ever needed — it is not, yet |
| **Agent Memory**, AI Search, Artifacts, Flagship | **GA** | Problem 7 thread state; flags for metering |
| **MCP** (`createMcpHandler`, `workers-oauth-provider`) | first-class, reference architecture | §5.4, the strategic bet |
| Email **Routing** (inbound) | **GA, free, all plans** | Problem 7's ear |
| Email **Sending** | **public beta** since 2026-04-16 | Problem 7's mouth — beta, so plan a fallback |
| Queues | GA, 1M ops/mo included | Backpressure for Browser Run's 120-browser cap |
| Cron Triggers | GA, up to 15 min CPU | Nightly rebuild; `describe.py` scheduling |
| **Agents SDK** | **preview** ("next edition", pre-1.0) | **Do not build v1 on it** |

The honest read: **everything problems 3–7 need is GA except the two things
that are not on v1's path.** Email Sending is beta but inbound Routing — the
half problem 7 actually needs first — is GA and free. The Agents SDK is preview
and moving fast; Workflows plus a plain Durable Object does everything the
roadmap needs today, is GA, and does not tie the codebase to a pre-1.0 API. If
the Agents SDK stabilises, adopting it later is a refactor behind the §6 seam.

**Can Browser Run actually drive a Greenhouse form in 2026?** Mechanically, yes
— it is full Puppeteer/Playwright with CDP access, the default 60-second
inactivity timeout extends to 10 minutes via `keep_alive`, and paid concurrency
is 120. What the documentation does **not** say anything about is CAPTCHA,
anti-bot behaviour, or file uploads — I looked and the limits page is silent, so
this document will not claim it. Résumé upload in particular is the step most
likely to break and the one nobody has tested here. **Treat "Browser Run can
submit a Greenhouse application end-to-end" as unproven until somebody runs it
once against a real posting.** It is a half-day experiment and it should happen
before problem 3 is scheduled, not during.

### 4.2 Vercel — good, and not worth the switch

Next.js + AI SDK + Workflow DevKit + Sandbox (Firecracker) + **eve** (released
2026-06-17, Apache-2.0, filesystem-first: an agent is a directory, Markdown for
instructions and skills, TypeScript for tools; durable checkpointed sessions,
per-agent sandboxes, subagents, evals, human-in-the-loop; Vercel says it runs
100+ agents on it in production). It is a coherent, well-made stack and eve is
the most pleasant agent-authoring model of the four options.

It buys, honestly: a nicer agent-authoring experience, and durable sessions that
survive deploys with less ceremony than hand-rolled Workflows.

It costs: **a second cloud, a second identity story, a second storage story, and
the abandonment of a Worker that already has Clerk auth, D1, R2, 128 passing
tests and eight canonical profile fields locked against Article 9 data.** For a
sandbox bill that is 60% *higher* on the same workload and 1.7% of the total.
The repo is zero-dependency, no-bundler, `node --test` — Next.js is a large
philosophical import for a codebase that has deliberately refused every
dependency so far.

**Verdict: no.** Revisit only if Cloudflare's agent story stalls, and revisit
with eve specifically — it is the part worth wanting.

### 4.3 Anthropic Managed Agents / Agent SDK — a runtime, not a host

The framing in the brief ("where should this live") makes this look like a
competitor to Cloudflare. It is not. Managed Agents is a **server-side agent
loop with a per-session sandbox** that a Cloudflare Worker calls over HTTPS. The
two compose; they do not compete.

Pricing (measured, as of 2026-08-03): **$0.08 per active session-hour**, metered
to the millisecond, accruing only while the session status is `running` — idle
time is free, and container hours are folded in rather than billed separately.
Tokens bill at standard per-model rates. Web search is $10 per 1,000 searches.

Map it onto the roadmap and the session fee disappears into the noise: a
90-second form fill is 0.025 session-hours = **$0.002**, against $0.147 of
tokens for the same fill. **The session fee is 1.4% of what the session costs.**
So Managed Agents is not expensive — but it is also not *cheaper*, because the
expensive part is the tokens, and those are the same wherever the loop runs.

What it genuinely offers problems 3–7: **vaults** (credentials stored by
Anthropic, substituted at egress, never visible in the sandbox — the right answer
for employer board API keys if the partner path in §5.3 happens), **scheduled
deployments** (cron-fired sessions, which is problem 7's "watch my inbox"
without a scheduler), **memory stores**, and **computer use** for the forms
Browser Run cannot drive.

What argues against it for v1: it is **beta**; it is a second vendor's control
plane for orchestration Cloudflare Workflows already does at GA; and — the
decisive one — **`HANDOFF.md` measured Managed Agents returning `403 scope` on
this account.** It is not merely unfunded, it is unreachable today.

**Verdict: not v1. The right shape is a Worker that calls the Claude API
directly through one seam (§6), so that swapping that seam for Managed Agents
later is a file, not a migration.**

**Does the founder's own use case need it?** Note one thing carefully:
`describe.py` already drives **Claude Code agents** on a subscription and that
is why descriptions have no per-user cost. For a **single-user tool** — which is
what this is for the next several months — that trick keeps working. It stops
working the moment a second person's applications run through it, because the
subscription cannot serve API traffic. **The founder can build and use problems
3–7 for himself at approximately zero marginal cost, and cannot sell them to
one other person without a funded API account.** That is the sharpest way to
state the billing finding, and it means the API purchase can honestly be
deferred until the first non-founder user exists.

### 4.4 MCP — take it seriously, because the economics invert

Every option above pays for inference per user. **An MCP server does not.**

Expose the corpus as a remote MCP server on a Worker — Cloudflare has
first-class support (`createMcpHandler`, streamable HTTP at `/mcp`, the
`workers-oauth-provider` library handling OAuth so you do not) — with a small
tool surface:

```
search_roles(query, city, department, hide_giants) → role rows with apply URLs
company_verdict(name)                             → the verdict card of STRATEGY §5
company_gate(name)                                → the admission receipt of PRODUCT-1 §2
corpus_funnel()                                   → 10,125 read · 6,895 rejected
```

Costs at 10k callers × 200 calls/month: 2M Worker requests against 10M included.
**Marginal cost ≈ $0, and the caller's own Claude subscription pays for all the
reasoning.** It is the only line in this document that gets cheaper per user as
users arrive.

It is also the honest form of the "AI-native" pitch. `STRATEGY.md` §4 explicitly
refuses "AI-native" as a differentiator because every competitor claims it and
it selects for the auto-apply arms race the doctrine already rejects. **Being
the tool other agents call is a different claim, and it is one the corpus can
actually back:** nobody else has a verified register with checked-vs-unchecked
honesty and explicit sponsorship negatives, and an agent asking "is this job
real" has nowhere else to ask.

Two cautions. First, MCP is a **distribution** bet, not a revenue one — there is
no metering story in it yet, and giving the corpus away to agents is giving away
the asset unless the referral layer is what gets sold. Second, it needs the
hosting move in §5.1 first, because an MCP endpoint is another public route on a
hostname that currently cannot terminate TLS.

**Verdict: build it, but after feature 1 ships and after the hosting move. It is
small, it is strategically distinct, and nothing else in the roadmap does what
it does.**

---

## 5. Recommendation

### 5.1 Decide now — before or with feature 1

**(a) Take ladder step 4's hosting move now, not later.** Serve the site from
the Worker on `roleatlas.sennamind.com`. Re-measured today, the three-level API
hostname still fails TLS and the two-level site hostname returns 200. `HLD-v5.md`
already found this: serving from the Worker **deletes** the TLS problem and the
CORS allowlist rather than fixing them. Every later feature — `PUT /keeps`, the
MCP endpoint, an inbound email webhook, a Workflow status endpoint — needs a
public route on a hostname that works. Doing it once, now, before there are four
consumers of it, is much cheaper than four times later.

The caveat is real and `HANDOFF.md` names it: **`index.mjs:104` runs
authentication before every handler without exception**, and a public route has
to be added there deliberately. That line is the most dangerous one in any future
change. Serving the site means adding exactly one public route, with a test that
goes red if a second one appears by accident.

The sequencing tension is also real: ladder step 3 (the soft gate) exists to
*measure* whether anyone signs in, and step 4 was supposed to wait on that
evidence. Nothing here overrides that. **The hosting move is justified on its own
— by a broken hostname and four pending consumers — not by step 3's verdict.**
Step 3 still decides whether the *sign-in wall* is worth building. Those are two
decisions that `HLD-v5.md` bundled and should stay unbundled.

**(b) Key state on the company.** `PRODUCT-1.md` §5 argues it from the product
side. The platform side agrees for a harder reason: the referral endgame's unit
is company + person, and a migration of user state after real users exist is the
single most expensive kind of change in this roadmap. Free today, costly later.

**(c) Put the seams in (§6).** One file for model calls, one for corpus queries.
Perhaps 100 lines. Everything deferred below stays cheap only because of them.

### 5.2 Defer deliberately

The agent runtime, Browser Run, email ingestion, and MCP. **None is needed for
problems 1 or 2**, all four are GA-or-better whenever they are wanted, and each
is roughly a week's work behind the §6 seams. Deferring them costs nothing.
Choosing one now costs the option to choose differently — and the Agents SDK is
preview, which is exactly the wrong maturity to commit to before you need it.

**Defer the funded API account too**, until the first non-founder user. §4.3
explains why that is honest rather than optimistic.

### 5.3 The one thing to re-plan: problem 3 is two products

This is the recommendation with the most consequence, and it comes from measured
facts rather than preference.

**Path A — the sanctioned path, for partners.** Greenhouse's Job Board API
exposes `POST /v1/boards/{board_token}/jobs/{id}`, multipart, with the questions
array readable in advance (which `questions.mjs` already parses). It
authenticates with HTTP Basic where the username is **the board's API key** — an
employer credential. Greenhouse's docs say the post must be proxied by your own
servers because a direct post would leak the key, and they explicitly recommend
their embedded form over a custom one, citing its fraud protection. Read that
plainly: **Greenhouse anticipates a server holding an employer's key and posting
on candidates' behalf. That is a partner integration, and it is sanctioned.**
It also happens to be exactly the "registered partners, not scraping" model the
founder already committed to for referrals. The same partner relationship
unlocks both. Credentials belong in a vault (Managed Agents' vaults, or Worker
secrets) — never in D1, never in a prompt.

**Path B — the assist path, for everyone else.** Ashby and Lever publish no
questions at all (measured), and **401 of 880 slugs are Ashby**. For roughly
half the register there is no API and never will be. Browser Run fills the form
and **a human presses submit** — which is what SPEC v4's non-goals already
require, what Browser Run's human-in-the-loop and Live View features are built
for, and what keeps this out of the S5 auto-apply arms race `STRATEGY.md` §2.5
tells the founder to stop relitigating.

Two products, two economics, two risk profiles. Planning problem 3 as one
feature will produce a design that is wrong for both halves.

### 5.4 Build the MCP server after feature 1

Small, strategically distinct, marginal cost ≈ zero, and the only thing here
whose economics improve with scale. §4.4 has the argument.

---

## 6. The portability rule

The point of this section is that **§5.2's deferrals stay cheap**. Two seams and
three prohibitions.

**Seam 1 — every model call goes through `llm.mjs`.**

```js
// takes fetch as a parameter, exactly as auth.mjs and questions.mjs already do
export async function complete({ system, messages, tools, model, fetch }) { … }
```

Plain `fetch` against `POST /v1/messages`. **No vendor SDK, no framework
client.** The repo is zero-dependency and no-bundler; keep it that way. Swapping
this file for Managed Agents' `sessions.create` + event stream, or for an AI
Gateway, or for Bedrock, becomes one file rather than a migration. `describe.py`
already proves the pattern — it drives agents behind an interface, which is why
the subscription-vs-API distinction was containable at all.

**Seam 2 — every corpus query is a tool function, defined once.**

```js
export const tools = [
  { name: "search_roles",     schema: {…}, run: (args, corpus) => … },
  { name: "company_verdict",  schema: {…}, run: (args, corpus) => … },
];
```

The same array feeds the MCP server (§4.4), a Claude API `tools` parameter, a
Managed Agents custom tool, and the page's own filter logic. **Write the query
logic once and the agent-runtime choice stops mattering.** This is the single
highest-leverage 50 lines in the plan.

**Three prohibitions:**

- **No framework in the request path.** Workflows, Durable Objects and the
  Agents SDK all have opinionated APIs. Business logic goes in plain modules that
  take their dependencies as arguments — the pattern that already let
  `profile.mjs`, `resume.mjs` and `questions.mjs` be built in parallel with no
  infrastructure and tested under `node --test` on a machine where workerd will
  not start. Orchestration calls into that logic; logic never imports
  orchestration.
- **Schema before storage.** The eight canonical profile fields are a vocabulary
  two modules already agree on. Any new state — application records, thread
  state, keeps — gets its shape defined in one module before it gets a table, so
  moving it from D1 to DO SQLite (which §2.3 says will be necessary) is a
  storage change, not a redesign.
- **No prompt text in orchestration code.** Prompts live beside the tool
  definitions. A platform migration should never require reading a Workflow to
  find out what the model was asked.

**What is deliberately *not* portable, and should not be:** Clerk auth, D1, R2,
and the Worker route table. Those are load-bearing, built, tested, and
provisioned. Abstracting them "for portability" would be speculative
generality — the exact thing to refuse when the recommendation is to stay put.

---

## 7. Honest risks

**1. The per-user LLM cost wall — the largest number in this document.**
$21/user/weekend against $15–30/user/month (§2.2). At 10k users doing 100
applications a month, tokens cost ~$210,000/month against ~$200,000/month of
subscription revenue: **negative gross margin on the flagship feature.**
Mitigations, in order of leverage: meter applications per period from day one
(Flagship feature flags, or the same counter pattern `resume.mjs` already uses
for R2); route generation through the Batch API at 50% off; cache aggressively;
use Haiku 4.5 for extraction and classification and never for anything a human
will be judged on; and — the structural answer — **charge for the referral, not
for the applications.** `STRATEGY.md` §6.5 already concluded that seeker
subscriptions are a bridge and the referral marketplace is the business. This
section is the cost-side proof of the same thing.

**2. Automated submission and ATS terms — narrower than feared, and unresolved
in a specific way.** I tried to read Greenhouse's terms of use directly and
**every URL I tried returned 404 or redirected to a 404** — so this document
will not quote clause text it could not read. What I could establish: Ashby's
published terms are a **Customer** agreement between Ashby and the employer, not
between Ashby and a candidate; no candidate-facing acceptable-use policy is
publicly discoverable for Ashby or Lever. **The ATS contract is with the
employer, not the applicant.** The real exposure is therefore three other things:
the *employer's own* career-site terms, which vary per company and nobody has
read; ATS-side anti-fraud machinery (Ashby ships real-time application fraud
detection and per-candidate application limits; Greenhouse's docs cite fraud
protection on their embedded form); and anti-circumvention exposure if a system
defeats those controls. **Path A (§5.3) has an employer's explicit permission and
carries none of this. Path B with a human pressing submit carries very little.
Fully automated submission at volume carries all of it.** The doctrine already
chose correctly; this is the legal reason it was right. Before problem 3 ships,
someone should read the terms on three actual employer career pages — that is an
hour of work and it is not optional.

**3. Browser Run against a real form is unproven here.** The docs are silent on
CAPTCHA, anti-bot behaviour and file uploads (§4.1). Résumé upload is the likely
breaking point. Half a day of experiment, before problem 3 is scheduled.

**4. Email access is the hardest consent problem in the roadmap, and it is not
a cost problem.** "An agent that watches my inbox" means holding an OAuth token
that can read everything a person receives — bank mail, medical mail, mail about
other people who never consented. This repo already refuses Article 9
special-category data in two independent places and has no column that could
hold it; **an inbox is a superset of everything `schema.sql` was written to keep
out.** The narrow design: a dedicated alias or a `+tag` address that applications
are sent from, received through Cloudflare Email Routing, so the product sees
replies to its own applications and *nothing else*. This is architecturally
easier than full mailbox access, free on Cloudflare, and it is the only version
consistent with what the repo already believes. **Do not ship full inbox OAuth.**

**5. LinkedIn referral mining — already ruled out, recorded here so it stays
ruled out.** Registered partners, not scraping. LinkedIn's user agreement
prohibits third-party automation and it enforces behaviourally. Nothing in this
document reopens it.

**6. Platform maturity, in the two places it actually bites.** The Agents SDK is
preview (do not build v1 on it — Workflows is GA and sufficient); Email Sending
is public beta (inbound Routing, which problem 7 needs first, is GA and free —
but have a fallback sender in mind for outbound). Everything else on the path is
GA.

**7. Single-vendor concentration.** Compute, storage, auth-adjacent routing,
DNS, TLS, email and browser automation would all sit with Cloudflare. That is
real concentration risk and the §6 seams do not remove it. It is accepted
knowingly: the alternative is running two clouds for a product with one
developer, and the mitigation that matters — the data is plain JSON, SQLite and
S3-compatible object storage — is already true.

**8. What this document did not check.** Cloudflare's contractual position on
driving third-party forms from Browser Run; whether AI Gateway would meaningfully
cut the §2 bill through caching; and Managed Agents' rate limits at the volumes
in §2.3. None blocks the recommendation; all three want an answer before problem
3 is built at scale. **An unchecked thing is unchecked, not fine.**

---

## 8. In one list

1. **Ship feature 1 on Workers static assets.** Free, unlimited, decided.
2. **Move the site onto the Worker** at the two-level hostname; delete the TLS
   and CORS problems; add exactly one public route at `index.mjs:104`, with a
   test that goes red if a second appears.
3. **Add the two seams** (`llm.mjs`, the tool-function array) — ~100 lines that
   keep every deferral cheap.
4. **Key user state on the company**, witnessing opened role URLs.
5. **Build the MCP server** over the tool-function array. Small, distinct,
   marginal cost ≈ zero, economics improve with scale.
6. **Re-plan problem 3 as two products** — partner API path, and browser-assist
   with a human pressing submit — before writing any of it.
7. **Prove Browser Run against one real Greenhouse form**, résumé upload
   included, before scheduling problem 3.
8. **Read three real employer career-page terms.** One hour, not optional.
9. **Buy the API account when the first non-founder user exists**, not before.
10. **Meter applications from the first line of code**, because $21 a weekend
    against $20 a month does not survive being popular.
