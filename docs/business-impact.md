# Business impact

The assignment asks for *"a business goal, stated as a number"*, and warns
against inventing one. This was deliberately left until after the data was
trustworthy. Three things are kept strictly apart below, because it is easy to
slide from one to the next without noticing.

---

## The headline

> **Cut avoidable refund leakage from 14.6% of refund spend to 3.7%, worth about
> ₹1.22 lakh a quarter (₹4.87 lakh a year).**

Baseline: **₹11,18,322** of refunds per quarter — the reconciled figure, not the
₹1 crore in the Finance export.

---

## Part 1 — OBSERVED FACT

Five buckets of avoidable cost. Every one is a named set of `ticket_id`s you can
open in the tool; none is estimated from a rate. **A ticket is counted in at
most one bucket** — the buckets are applied in priority order and later buckets
exclude tickets already claimed, so nothing is double counted
(`test_impact_buckets_do_not_double_count`).

| # | Bucket | Tickets | What is counted | Per quarter |
|---|---|---:|---|---:|
| 1 | Duplicate remedy: refund **and** replacement on the same order | 202 | the **cheaper** of the two remedies only | **₹59,732** |
| 2 | Pricing/coupon refunds — discount not applied at checkout | 106 | the refund | **₹46,238** |
| 3 | Handling cost of payment-failure contacts | 511 | the **contact cost only**, not the refund | **₹25,631** |
| 4 | Refund released without the unit being collected | 41 | the refund | **₹17,270** |
| 5 | Genuine goodwill above the ₹500 cap (after restatement) | 28 | the **excess over ₹500** only | **₹14,674** |
| | **Total identified** | **888** | | **₹1,63,545** |

**= 14.6% of quarterly refund spend.**

### Why each number is smaller than it could have been

Every bucket is deliberately deflated:

- **Bucket 1** counts only the *cheaper* remedy. The customer received both a
  refund (₹6.93 L) and a replacement (₹3.60 L); we claim ₹3.58 L, not ₹10.53 L.
  Claiming both would have doubled the headline and been wrong — one remedy was
  legitimately owed.
- **Bucket 3** excludes the refund entirely. A duplicate-payment refund returns
  money that was wrongly collected; it is cash churn, not a P&L loss. Only the
  ₹210–₹520 contact cost (policy §4) is avoidable. Including the ₹13.76 lakh of
  refunds here would have tripled the headline and been economically illiterate.
- **Bucket 5** counts only the excess over the cap, and only on the 65 tickets
  the text supports as *genuine* goodwill — not on all 991 booked that way.

### Buckets deliberately NOT claimed

| Not claimed | Per quarter | Why |
|---|---:|---|
| Legitimate returns (RETURN-QC-OK) | ₹3.64 L | The customer sent the product back. Reversing a sale is not leakage. |
| Cancellations before dispatch | ₹1.61 L | No sale happened. Not a loss. |
| Duplicate-payment refunds themselves | ₹2.29 L | Money wrongly collected, returned. Net zero. |
| Transit loss and damage | ₹1.45 L | Real cost, but recovery runs through carrier claims — outside this dataset, so unquantifiable here. |
| Warranty buy-backs | ₹0.99 L | The cost of selling hardware. |

Had we counted everything that *looks* like a refund, the "opportunity" would
have read ₹11 lakh a quarter. That number would not have survived Arjun's first
question.

---

## Part 2 — POTENTIAL OPPORTUNITY

What could be recovered, with the reduction factor stated and argued rather than
assumed.

| Bucket | Observed/qtr | Reduction | Saving/qtr | Reasoning |
|---|---:|---:|---:|---|
| Duplicate remedy | ₹59,732 | **90%** | ₹53,759 | Policy §5 says the target is zero. 90% allows for genuine exceptions escalated to Finance. |
| Pricing/coupon | ₹46,238 | **70%** | ₹32,367 | Each is a checkout defect refunded after the fact. 70% leaves room for real price-drop goodwill. |
| Payment-failure handling | ₹25,631 | **70%** | ₹17,942 | Reliable order creation on payment removes most of the contacts. |
| Refund without collection | ₹17,270 | **60%** | ₹10,362 | Some releases are a deliberate service call; 60% reflects that. |
| Goodwill over cap | ₹14,674 | **50%** | ₹7,337 | Deliberately cautious — some may have had Team Lead approval the export does not record. |
| **Total** | **₹1,63,545** | | **₹1,21,767** | |

**₹1,21,767 per quarter ≈ ₹4,87,068 per year.**
Avoidable leakage falls from **14.6% → 3.7%** of refund spend.

---

## Part 3 — RECOMMENDED TARGET

**Two quarters. One owner per bucket. Measured by re-running this tool.**

| Quarter | Action | Owner | Target |
|---|---|---|---|
| Q1 | Block refund + replacement on the same order in the helpdesk | Sameer (IT) | Bucket 1 → near zero |
| Q1 | Make GW-OTHER **not** the default dropdown option; require a reason | Sameer (IT) | Restores the board pack — see below |
| Q1 | Fix order creation on payment success | Payments / IT | Bucket 3 |
| Q2 | Coupon validation at checkout | E-commerce | Bucket 2 |
| Q2 | Enforce pickup-before-refund, and the ₹500 cap with TL approval | Neha (Support Ops) | Buckets 4, 5 |

The measurement is the tool itself: re-run it next quarter and the same five
buckets recompute from the same source columns.

---

## The change that costs nothing

The single highest-leverage fix is not in the table above because **it saves no
money directly**. Sameer Qureshi flagged it in his first email:

> *"the first option in the list is GW-OTHER (Goodwill / Other) and agents are agents."*

**991 refunds — ₹29,07,036, 43.3% of all refund value — are booked to the
dropdown default. The free text supports genuine goodwill on 37 of them (₹1,35,652, 2.0%).**

| Reason | Recorded | Restated from the text |
|---|---:|---:|
| Goodwill / Other | **43.3%** | **2.0%** |
| Return received & QC'd | 17.6% | 32.6% |
| Duplicate/failed payment | 13.2% | 20.5% |
| Cancellation | 9.1% | 14.4% |
| Warranty buy-back | 4.3% | 16.5% |
| Lost in transit | 2.3% | 7.5% |
| Dead on arrival | 7.0% | 5.3% |
| Price/coupon | 3.1% | 4.1% |

Reordering one dropdown makes the next 18 months of this report self-evidently
correct, with no analysis layer required. Every bucket in Part 1 was only
findable *because* we could see past the default — buckets 2, 4 and 5 are
largely tickets currently sitting inside GW-OTHER.

**Observed fact.** The recorded code and the free text disagree on 96% of
GW-OTHER refunds, against 9.6% disagreement on every other code
(`docs/validation.md`, Layer 4).
**Not claimed.** That agents are being careless, dishonest, or generous. The
first option in a dropdown gets picked; that is a UI fact, not a people fact.

---

## What we are explicitly not claiming

- **No causality.** Refund value roughly doubled between Q1 2025 and Q4 2025, but
  ticket volume more than doubled over the same period and the refund *rate* is
  flat at 18–22% across all six quarters. Refunds went up because contacts went
  up. We do not know why contacts went up; nothing in this pack answers that.
- **Priya Raman's Q4 hypothesis is not supported.** There is no Q4 step change in
  the refund rate, and CSAT sits at 3.46–3.54 across all six quarters — a range
  of 0.08, not the stated +0.4. This is reported as a measurement, not a rebuttal.
- **No agent is named as a problem.** Policy §6 states the Returns Desk
  processes most refunds by design and that Tier 2 must not be compared on
  volume. The top three agents by refund value sit on the three refund-owning
  teams. See `docs/decisions.md` D-15.
- **The ₹4.87 lakh is an opportunity, not a forecast.** It assumes the five fixes
  are made and hold. We have no data on implementation cost, and have not netted
  it off.
