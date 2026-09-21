# Submission form — Vireo Audio, Support Tickets (Set C)

> **Note on this file.** `assignment.txt` says *"Complete `submission-form.md`
> from this pack."* No file of that name was in the pack (9 files received). The
> questions below are reproduced **verbatim and in order** from the end of
> `assignment.txt`. Logged as decision D-01.

> **Three fields need your details before you submit** — they are marked
> `«FILL IN»`: the Drive link, the GitHub URL, and honest hours.

---

### 1. What did you build, and what business outcome does it move? State the number and the money.

A reconciliation and refund-analysis tool for Vireo's helpdesk export: a Python
pipeline producing a canonical refund table, a monthly summary by reason code
and by agent, and a Streamlit reviewer where any figure can be traced to its
source ticket.

**The first outcome was correcting the number itself.** Finance was reporting
over ₹1 crore a quarter; the helpdesk said ~₹11 lakh. The reconciled figure is
**₹11,18,322 per quarter**. The gap is legacy Freshdesk storing money in paise
(99.4% of it) plus 638 duplicate rows from the migration re-import. The bridge
from ₹23,01,24,081 to ₹67,09,932 closes with **zero residual**.

**The business goal, as a number:**

> **Cut avoidable refund leakage from 14.6% of refund spend to 3.7% — ₹1,21,767
> per quarter, ₹4,87,068 per year.**

Five mutually-exclusive buckets, 888 named tickets, no estimates from rates:

| Bucket | Tickets | Observed/qtr | Target saving/qtr |
|---|---:|---:|---:|
| Refund **and** replacement on the same order (policy §5 breach) | 202 | ₹59,732 | ₹53,759 |
| Coupon/discount not applied at checkout, refunded later | 106 | ₹46,238 | ₹32,367 |
| Handling cost of payment-failure contacts | 511 | ₹25,631 | ₹17,942 |
| Refund released before the unit was collected | 41 | ₹17,270 | ₹10,362 |
| Goodwill above the ₹500 cap (after restatement) | 28 | ₹14,674 | ₹7,337 |
| **Total** | **888** | **₹1,63,545** | **₹1,21,767** |

**The largest finding moves no money directly but fixes the deliverable:** 991
refunds (₹29,07,036, **43.3%** of refund value) are booked to `GW-OTHER`, the
first option in the agent's dropdown. The free text supports genuine goodwill on
**37 of them (2.0%)**. Reordering one dropdown makes the board pack correct
permanently.

---

### 2. What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.

Computed by `vireo/costs.py` from the data, not estimated by hand.

**Architecture drives the answer.** Two tiers: deterministic rules resolve
**2,215 of 2,340 refunds (94.7%)** for nothing; only the **125 (5.3%)** that are
genuinely ambiguous reach a model.

**One full run — all 18 months, 2,340 refunds:**

```
tier 1 (rules)      2,215 tickets      0 tokens        ₹0
tier 2 (model)        125 tickets, 3 batches of 50
  input   = 125 ticket texts (~64 tok each) + prompt (~900 tok × 3 batches)
          = 10,301 tokens
  output  = 125 × 45 tok  = 5,625 tokens

Claude Haiku 4.5  ($1/M in, $5/M out):
  10,301/1e6 × $1  +  5,625/1e6 × $5  =  $0.0103 + $0.0281 = $0.0384  ≈ ₹3.38
Claude Sonnet 4.5 ($3/M in, $15/M out):                      $0.1153  ≈ ₹10.14
```

**Monthly at 650 tickets/week:**

```
tickets/month     = 650 × 52 / 12                    = 2,817
refund rate       = measured from the data, not assumed = 20.2%
refunds/month     = 2,817 × 0.202                    = 568
escalation rate   = measured                          = 5.3%
model calls/month = 568 × 0.053                      = 30
  input  = 30 × 64 + 900 (1 batch)                   = 2,481 tokens
  output = 30 × 45                                   = 1,355 tokens

Haiku 4.5:  2,481/1e6 × $1 + 1,355/1e6 × $5  = $0.0093  ≈ ₹0.81/month
Sonnet 4.5:                                    $0.0278  ≈ ₹2.44/month
```

**Comparison:** sending every refund to the model would cost **₹46.11/month** —
the two-tier design is **94.7% cheaper**.

**Honest caveat:** ₹46/month would also have been fine. The API cost was never
going to be the constraint. The two-tier design earns its place because 94.7% of
labels are reproducible with no key, no network and no vendor — and because
pointing the model only at hard cases is what makes measuring its accuracy
meaningful. **The real cost of this system is build time, not inference.**

**Paid calls actually made during the build: none.** This environment had no
`ANTHROPIC_API_KEY`. The classifications were produced by Claude Opus 5 through
Claude Code, reading each ticket against `prompts/reason_classifier.md`. The
`anthropic` backend is written, reviewed and **unexercised** — see Q5.

---

### 3. How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.

Four layers. Full detail in `docs/validation.md`.

**a) Reconciliation.** Residual **₹0.00**. Six identities
(`Σ monthly = Σ reason = Σ agent = canonical total`, and the same for counts) all
PASS. The pipeline refuses to write output otherwise.

**b) The conversion factor is self-proving.** The ÷100 is not trusted from
config — `verify_legacy_conversion()` re-derives it from the data on every run
and aborts if it changes. 125 pairs, ratio 100.0, std dev 0.0; 775/775 legacy
amounts divisible by 100. Strongest evidence: **after** conversion, 125 of 125
duplicate pairs agree to the rupee across both systems, 0 disagree.

**c) Independent recomputation + record sample.** `vireo/validate_sample.py`
imports none of the transformation code — it reads the CSV with stdlib `csv` and
re-derives every field itself.

| | |
|---|---|
| Independent total vs pipeline | ₹67,09,932 = ₹67,09,932 · PASS |
| Sample size | **60 canonical refund records**, `seed=20260921` (reproducible) |
| Checks per record | 15 → **900 field checks** |
| **Error rate** | **0.00% of records, 0.000% of field checks** |

**d) AI accuracy, measured against a 168-ticket gold set:**

| | |
|---|---|
| Tier-1 resolved | 159/168 (94.6%) |
| **Accuracy on what it resolves** | **97.5%** (155/159) |
| Control — agreement with the *recorded* code on 1,349 non-GW refunds | **90.4%** |

Locked by a test that fails the build if accuracy drops below 95%.

**The kind of case it gets wrong.** All four tier-1 errors are the boundary
between *genuine goodwill* and *the problem that preceded it* — e.g. TK-241675,
where a pairing fault was resolved and a refund was given anyway. Three of four
are this same shape. It is a hard call for a human, and it is where being wrong
costs least: both labels agree the ticket is unusual, and the rupee total is
unaffected either way.

Also: 71 tests pass, covering duplicates, the legacy unit, missing values,
joins, roster resolution, conflicts and aggregation.

---

### 4. Did you change, narrow, or push back on the client's ask? What, when, and why.

Four times.

**1. Refused to rank agents** (decision D-15, made during the Step 1 audit).
Arjun asked *"who is giving away money"*. The three agents with the largest
refund totals sit on Returns Desk, Billing and Logistics. Policy §6 states the
Returns Desk *"processes the large majority of refunds by design"* and that
Tier 2 *"are not to be compared with Tier 1 on volume"*. A league table would
have ranked people for doing their jobs. We ship exposure-adjusted context
(tickets handled, refund rate, team, tier) and one genuinely comparable signal —
GW-OTHER share, which ranges 24%–99% on similar work.

**2. Made reconciliation the primary deliverable, not a footnote.** Arjun asked
for a summary and mentioned reconciling almost in passing. The reconciliation
turned out to be the entire story: the summary would have been 100× wrong
without it.

**3. Reported the recorded reason codes *and* what the text says, side by side.**
A summary by reason code alone would have been a summary of a dropdown defect.
We never overwrite the recorded code (D-16) — both columns travel together.

**4. Contradicted the framing that refunds are the problem.** The refund *rate*
is flat at 18–22% across all six quarters. Contacts more than doubled. Also, on
the record: Priya Raman's stated +0.4 CSAT improvement does not appear — CSAT
sits at 3.46–3.54 throughout, a spread of 0.08. Reported as a measurement, not
a rebuttal.

---

### 5. What is wrong with what you are handing us? Be specific: bugs, shortcuts, things you know are off.

1. **Tier-2 AI accuracy is unmeasured, and I will not fake a number for it.** The
   tier-2 labels and the gold set came from the same model, so measuring one
   against the other would be circular. Affects 125 tickets (5.3% of refunds,
   6.1% of value). Fix: hand-label 50 tickets, ~1 hour.
2. **The `anthropic` backend has never been run.** No API key in the build
   environment. The code is complete and reviewed but unexercised — treat it as
   untested until someone runs it once.
3. **Replacement-conflict detection in free text is high-precision, low-recall
   by design.** The true count is **≥** 202. I chose to under-count rather than
   over-claim, but it does mean the ₹53,759/quarter figure is a floor.
4. **707 refund tickets have an ambiguous order join, left unresolved** (D-06).
   Context only — a test asserts no reported total depends on the order join.
5. **The ÷100 evidence comes only from pairs dated Jan–Sep 2025.** If the legacy
   unit changed earlier we could not see it. Mitigated by divisibility holding
   across all 775 legacy amounts, but not eliminated.
6. **Month = `created_at`, which is a ticket-cohort view, not cash-out.** 80 of
   2,340 refunds (3.4%) land in a different month on the other basis. If Finance
   wants accounting months, `month_resolved` is already computed but the memo
   figures would shift slightly.
7. **D-05 is an unproven assumption** underpinning the whole narrative: that the
   file Arjun added up is the file Sameer sent us. Flagged in the memo.
8. **The UI is one Streamlit file with one chart.** Deliberate, but it is not
   something you would hand a board directly.
9. **A test caught a real bug mid-build**, which I mention because it shows the
   class of thing that could still be hiding: `attach_agents` had a fast path
   that skipped date validation and would have mis-reported roster matches.
   Today's data has one row per agent so no output was wrong, but the next
   export with a transfer in it would have been.

---

### 6. What did you deliberately leave out, and why that rather than something else?

Full reasoning in `docs/scope.md`. The main ones:

- **Anything that reduces the *number* of refunds.** The biggest true category is
  legitimate returns (₹3.64 L/qtr). Cutting them means changing the product,
  listings or returns policy, and nothing in the pack says which. That would
  have been exactly the generic best-practice advice the brief warns against.
- **Root cause of the volume doubling.** The most valuable open question here.
  Needs sales volume, launch dates and marketing spend — none supplied. Flagged
  as the next question rather than guessed.
- **Repeat-contact costing.** I built it and then dropped it: 23.0% of tickets
  are a second contact from the same customer about the same SKU within 30 days,
  ₹1.23 L/quarter. Policy §10 defines a repeat as being about *the same issue*,
  which I cannot verify from the data. Including it would have inflated the
  headline by 75% with a number I could not defend.
- **SLA breach and CSAT analysis.** Rich material in policy §3 and §8, but Arjun
  asked about refunds. I checked only far enough to confirm the ₹350 breach
  credits are not contaminating `refund_amount_inr` (D-11).
- **Carrier claim recovery** (₹1.45 L/qtr in transit loss and damage) — depends
  on contracts not in the pack.
- **Database, API, auth, Docker, CI, charts beyond one bar chart.** A 5-hour
  exercise producing a monthly board figure. *"A small thing that runs beats a
  large thing that does not."*

---

### 7. Anything you built or found that nobody asked for?

- **The 29 hidden refund+replacement conflicts.** Neha called these *"probably
  one-offs"*. There are 202, and 36 of them are invisible in the structured data
  — they only exist in what the agent typed (*"issued refund + replacement both,
  TL aware"* on a ticket flagged No). They are increasing: 19 → 52 per quarter.
- **A duplicate-pair natural experiment.** The 638 re-imported tickets turned out
  to be the proof of the paise conversion. Nobody designed that; the migration
  bug accidentally created a controlled experiment, and it is now the strongest
  evidence in the submission.
- **Priya's CSAT claim does not hold.** +0.4 was stated; the data shows 0.08 of
  movement across 18 months. Nobody asked us to check.
- **Policy §9 is wrong about `transfers`.** It says the field exists only in the
  current helpdesk; 340 legacy rows have it (D-12). No impact on refunds, logged
  so nobody later thinks we missed it.
- **The cost model itself** (`vireo/costs.py`) — the arithmetic in Q2 is code,
  not a spreadsheet, so it updates when prices or volume change.
- **A validation harness that shares no code with the pipeline.** Built because
  checking the pipeline by running the pipeline proves nothing.

---

### 8. What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away. Link your three-minute screen recording here.

**Tools and models:** Claude Opus 5 via Claude Code (Cowork), for the entire
build — audit scripts, pipeline, tests, docs — and as the tier-2 classifier and
the 168-ticket gold set. No other models. **No paid API calls** (see Q2).

**Where it helped most:**
- Reading 293 free-text ticket pairs individually to build the gold set and
  label the escalated tail. This is the one task that is genuinely infeasible by
  hand in the time and genuinely unsuited to regex.
- Writing the deterministic rules *from* that reading, which is why tier 1 hits
  97.5% rather than the ~60% a first-guess keyword list managed.

**Where it wasted time:**
- **My first plan was to send all 991 GW-OTHER tickets to a model.** I got 168
  through before stopping. It was the wrong architecture — expensive, slower, and
  it would have left me with an unmeasurable classifier. Rewriting it as
  rules-first cut model usage by 94.7% *and* produced a better accuracy story,
  because the 168 already-labelled tickets became the evaluation set instead of
  production output.
- An early regex pass had capture groups in it and threw pandas warnings for
  several runs before I noticed.

**What I threw away:**
1. **The all-tickets-to-LLM architecture** (above) — replaced by the two-tier router.
2. **A `drop_duplicates()`-based dedupe.** Wrong: 125 of the 638 pairs differ on
   amount, so it would have silently banked paise values as rupees. There is now
   a test that demonstrates the bug it would have caused.
3. **A `classify_cached` full-coverage backend** — superseded by the two-tier
   design; kept in the code as a fallback but no longer the default path.
4. **Repeat-contact costing** (Q6) — built, measured at ₹1.23 L/quarter, then
   dropped from the business case as undefendable.
5. **The first `attach_agents` implementation** — a fast path that skipped date
   validation. Deleted after a test caught it.
6. **A keyword-only "GW-OTHER is miscoded" claim** from the Step 1 audit. The
   keyword probes overlapped (payment 177, returns 181, transit 143) and could
   not adjudicate between them. That ambiguity is precisely what justified using
   a model at all.

**Screen recording:** «FILL IN — link»  (shot list in `deliverables/recording-plan.md`)

---

### 9. Your Public Google Drive Link

«FILL IN — public Drive link»

---

### 10. Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. **`data/derived/canonical_refunds.csv` is the only table any total may come
   from.** One row per ticket, amounts already converted to rupees. Sum anything
   else — especially `data/raw/tickets.csv` — and you will reproduce Finance's
   ₹1 crore.
2. **`reason_code` is a fact; `ai_suggested_reason` is an opinion. Never let the
   second overwrite the first.** The pipeline asserts that the AI layer cannot
   change a refund total. Keep that assertion; it is the load-bearing line in
   the architecture.
3. **The ÷100 legacy conversion is measured, not configured.**
   `verify_legacy_conversion()` re-derives it from the duplicate pairs on every
   run and aborts on disagreement. If a future export breaks that, the pipeline
   stopping is *correct behaviour*, not a bug to route around.

---

### 11. Honest hours spent. One number.

«FILL IN — one number»

*(For reference when you fill this in: Step 1 audit and documentation, Step 2
pipeline and 60 tests, Step 3 AI layer and UI, Step 4 validation and impact
model, Step 5 packaging. The assignment's cap is 5 hours and it says going over
is not rewarded.)*

---

### 12. Github Repo Link / Please upload your Github Repo URL (Public)

«FILL IN — public GitHub URL»
