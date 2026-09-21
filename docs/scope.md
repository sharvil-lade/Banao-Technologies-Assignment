# Scope decisions

The assignment says: *"There is more here than fits in five hours. That is on
purpose. What you choose to leave out, and whether you can say why, matters as
much to us as what you build."*

---

## What we built

| Built | Why it earned the time |
|---|---|
| Reconciliation bridge, raw export → canonical total, zero residual | Arjun asked for exactly this in writing. It is the deliverable, not a supporting detail. |
| Evidence-based legacy unit conversion, re-derived every run | The whole ₹1 crore vs ₹11 lakh question turns on it. An assumption here would invalidate everything. |
| Duplicate resolution with a full audit trail | 638 pairs, 125 with conflicting money. Getting this wrong silently changes the answer. |
| Deterministic monthly / reason / agent aggregation | The literal client ask: "who, how much, what for". |
| Policy flags with written evidence per ticket | Turns "suspicious" from an opinion into a citation. |
| Two-tier AI classifier (rules → model) | Answers "what for" properly, at ₹0.81/month. |
| Independent recomputation + 60-record sample | Answers "how do you know it works" with a number instead of an assertion. |
| Streamlit reviewer | A reviewer can check any figure against its source ticket in three clicks. |
| 71 tests | One of them found a real bug in the roster join. |

---

## What we deliberately left out

### 1. Anything that reduces the number of refunds
**Left out because the data cannot support it.** The biggest true category is
legitimate returns (₹3.64 L/quarter). Cutting them means changing the product,
the listings or the returns policy. Nothing in this pack tells us which, and a
recommendation without that evidence would be the "generic best practice" the
brief warns against.

### 2. Root-cause analysis of the volume increase
Tickets more than doubled (1,053 → 2,678 per quarter). That is the actual driver
of the refund increase and it is the most valuable open question here. Answering
it needs sales volume, product launch dates and marketing spend — none supplied.
**Flagged to the client as the next question rather than guessed at.**

### 3. Agent performance ranking
Not a time decision — a correctness one. See D-15. Policy §6 states in writing
that the Returns Desk processes most refunds *by design* and that Tier 2 must
not be compared with Tier 1 on volume. A league table would be the single most
damaging output this tool could produce. We ship exposure-adjusted context and
one comparable signal (GW-OTHER share) instead.

### 4. SLA breach and CSAT analysis
Policy §3 and §8 are rich, and the ₹350 breach credit is a real cost line.
**Out of scope: Arjun asked about refunds.** We checked only far enough to
confirm breach credits are *not* contaminating `refund_amount_inr` (D-11).

### 5. Repeat-contact / first-contact-resolution costing
We tested it: 23.0% of tickets are a second contact from the same customer about
the same SKU within 30 days, ₹1.23 L/quarter in handling cost. **Not included in
the business case**, because policy §10 defines a repeat contact as being about
*the same issue*, and we cannot verify "same issue" from the data. Including it
would have inflated the headline with a number we could not defend. Recorded
here as an observation worth a follow-up.

### 6. Resolving the 707 ambiguous order joins
Picking "the most recent order" would be a rule we invented. Since no reported
total depends on the order join — there is a test asserting exactly that — the
cost of leaving them unresolved is some missing context and zero correctness.

### 7. Carrier claim recovery
₹1.45 L/quarter sits in transit loss and damage, and policy §5 mentions damage
claims. Whether any of it is recoverable depends on carrier contracts that are
not in the pack.

### 8. A database, an API, auth, containers, CI
A 5-hour exercise producing a monthly board figure. CSV in, CSV out, one
Streamlit file. *"A small thing that runs beats a large thing that does not."*

### 9. Charts beyond one bar chart
The brief says not to spend time on visual design. The tool is built for a
reviewer checking numbers, not for a board slide. The memo carries the narrative.

---

## Where we pushed back on the client

| Asked for | What we did | Why |
|---|---|---|
| *"who is giving away money"* | Gave refund value **with** tickets handled, refund rate, team and tier — and no ranking | Policy §6. The highest-rupee agents are the people whose job is refunds. |
| *"summary by reason code"* | Gave the recorded codes **and** what the text says, side by side | The recorded codes are 43% dropdown default. A summary by reason code alone would be a summary of a UI defect. |
| *"the total to reconcile"* | Made the reconciliation the primary deliverable, not a footnote | It turned out to be the whole story. |
| Implicit: *refunds are the problem* | Showed refund **rate** is flat and volume is the driver | Contradicts the framing, but it is what the data says. |

---

## What we would do next, in order

1. **Hand-label 50 escalated tickets** (~1 hour) — closes the last measurement gap.
2. **Run the `anthropic` backend once for real** — the code is written and unexercised.
3. **Confirm Finance's export is this file** (D-05) — one email; the reconciliation narrative depends on it.
4. **Get ticket volume drivers** — the real question behind the refund increase.
5. **Cash-out month view** — if Finance wants accounting months, `month_resolved` is already computed.
