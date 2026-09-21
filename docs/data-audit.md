# Data Audit — Step 1

All figures below were produced by read-only scripts in `scripts/audit_01.py` … `audit_10.py`
against untouched copies of the supplied files in `data/raw/`.
**No source file was modified.**

---

## 1. Volumes

| File | Rows | Key | Notes |
|---|---|---|---|
| `tickets.csv` | **12,238** | `ticket_id` (not unique) | 21 columns. 11,600 distinct ticket_ids. |
| `agents.csv` | 44 | `agent_id` | 44 distinct agents, **one row each** |
| `orders.csv` | 15,000 | `order_id` | 15,000 distinct |
| `customers.csv` | 9,500 | `customer_id` | 9,500 distinct |
| `products.csv` | 14 | `sku` | 14 SKUs, 5 families |

Ticket window: 2025-01-01 09:17 → 2026-06-30 23:14 (18 months, as stated).

## 2. Null / blank rates (tickets.csv)

| Column | Blank | % | Comment |
|---|---|---|---|
| `resolved_at` | 622 | 5.1% | Exactly equals count of `open` + `pending` (358 + 264). Consistent — not missing data. |
| `order_id` | 4,127 | 33.7% | Expected: "Blank when the customer did not quote it." |
| `csat_score` | 6,729 | 55.0% | Policy §8: ~45% respond. Observed response 45.0%. Matches exactly. |
| `refund_amount_inr` | 9,773 | 79.9% | Blank = no refund. |
| `refund_reason_code` | 9,773 | 79.9% | **Identical count** to refund_amount blanks. |
| everything else | 0 | 0% | |

**Finding 2.1 (clean):** `refund_amount_inr` and `refund_reason_code` are perfectly co-present.
0 refunds with a missing reason code; 0 reason codes without an amount.
There is therefore **no "missing reason code" problem** in this dataset — a risk we expected and had to rule out rather than assume.

## 3. Duplicates

638 `ticket_id`s appear exactly twice. Every duplicate group is size 2. Every pair is
one `helpdesk` row + one `legacy_fd` row. No triples, no legacy/legacy, no helpdesk/helpdesk.

Column-by-column comparison inside the 638 pairs:

| Columns that differ | Count of pairs |
|---|---|
| `source_system` | 638 (by construction) |
| `refund_amount_inr` | **125** |
| **all other 19 columns** | **0** |

Every duplicate pair is byte-identical except the source tag and the money field.
Duplicate `created_at` range: 2025-01-01 → 2025-09-13 — i.e. entirely **before** the
helpdesk go-live of 14 Sep 2025 (policy §9).

Cross-check: exactly **638** `helpdesk` rows have `created_at` before go-live. That is the
re-imported subset and nothing else. 1 `legacy_fd` row sits after go-live (2025-09-14 01:19),
a boundary case, not a systemic overlap.

**Finding 3.1:** duplication is fully explained by the documented migration re-import.
It is not random data corruption, and it can be resolved deterministically.

## 4. The legacy money unit — resolved by evidence, not assumption

Policy §9: *"The legacy tool stored monetary values in its own native unit; the current
helpdesk stores rupees."* The unit is **not named** anywhere in the pack.

The 638 duplicate pairs are a natural experiment: the same refund, recorded by both systems.
125 of those pairs carry a refund amount on both sides.

| Test | Result |
|---|---|
| `legacy_fd ÷ helpdesk` across all 125 paired observations | **exactly 100.0** in 125 of 125 cases (std dev 0.0) |
| Legacy amounts divisible by 100 | **100.0%** (775 of 775) |
| Helpdesk amounts divisible by 100 | 5.5% (i.e. ordinary rupee prices like 2499, 1799) |
| Legacy median | ₹2,24,900 → ÷100 = ₹2,249 |
| Helpdesk median | ₹2,499 |

**Finding 4.1:** the legacy native unit is **paise**. Conversion is `÷ 100`.
This is established from 125 independent observations with zero variance, not inferred from
plausibility. Confidence: high. Residual risk documented in `decisions.md` D-03.

## 5. The ₹1 crore vs ₹11 lakh gap — reconciled

| Step | 18-month total | Per quarter |
|---|---|---|
| A. Naive sum of `refund_amount_inr`, all 12,238 rows as exported | **₹23,01,24,081** | ₹3.84 crore |
| B. less legacy paise→rupee correction (−₹22,30,53,138) | ₹70,70,943 | ₹11.78 lakh |
| C. less duplicate legacy twins (−₹3,61,011, 125 rows) | **₹67,09,932** | **₹11.18 lakh** |

Against the two client numbers:

- Arjun's *"well over a crore a quarter"* → reproduced by step A. The 2025 quarters alone
  sum naively to ₹6.1 cr, ₹7.3 cr and ₹9.2 cr. The cause is legacy paise read as rupees.
- Sameer's *"around Rs 11 lakh a quarter"* → reproduced by step C: **₹11.18 lakh/quarter**.

**Finding 5.1:** the helpdesk report is substantially right and the Finance export is wrong.
The entire discrepancy is (i) a unit error, ~99.4% of the gap, and (ii) duplicate rows, ~0.5%.
Nothing is missing from Finance's export; it is over-counted, not under-counted.

Note: a helpdesk-only view (ignoring legacy rows entirely) gives ₹48.2 lakh / 18 months
= ₹8.03 lakh/quarter, which **understates** the true figure for 2025 because pre-go-live
tickets are then missing. The correct answer is neither export as-is.

## 6. Risk register — every risk the brief named, investigated

### 6.1 Migration duplicates — **CONFIRMED, resolvable**
638 pairs (§3). Resolution rule and audit trail in `decisions.md` D-02.

### 6.2 Legacy vs current monetary representation — **CONFIRMED, resolved**
÷100 (§4).

### 6.3 Missing refund amounts — **NOT PRESENT**
0 rows with a reason code and no amount. 0 zero-value refunds. 0 non-numeric values.
Min ₹32, max ₹13,998, all whole rupees after normalisation.

### 6.4 Missing reason codes — **NOT PRESENT** (see 2.1)
But see 6.10: the codes that *are* present are not necessarily correct.

### 6.5 Refund **and** replacement on the same ticket — **CONFIRMED, larger than the client thinks**

Neha Kulkarni called these "probably one-offs". Policy §5: *"In no case is a customer to
receive both a refund and a replacement for the same order."*

| Source of signal | Tickets | Refund value |
|---|---|---|
| `replacement_issued = Y` **and** a refund amount | **166** | ₹5,74,191 |
| `replacement_issued = N` but the agent's note explicitly says both were given | **29** | ₹1,04,640 |
| **Total** | **195** | **₹6,78,831** |

The 29 hidden cases are only visible in free text. Example note (flag = N):
> *"issued refund + replacement both, tl aware. -VB"*

Adding the policy replacement cost (`unit_cost_inr` + ₹340 reverse-pickup/shipping, policy §5)
gives a combined exposure of **₹10,30,361 over 18 months = ₹1,71,727 per quarter**,
and the count is trending up (18 → 16 → 32 → 38 → 53 → 38 per quarter).

This is a candidate business goal. **Not yet committed** — see Step 4.

### 6.6 Invalid foreign keys — **NONE**
| Join | Result |
|---|---|
| ticket.`agent_id` → agents | 0 orphans (44/44 agents used) |
| ticket.`product_sku` → products | 0 orphans |
| ticket.`customer_id` → customers | 0 orphans |
| ticket.`order_id` → orders (where quoted) | 0 orphans (5,460 distinct) |
| order↔ticket `customer_id` agreement | 8,111/8,111 agree |
| order↔ticket `sku` agreement | 8,111/8,111 agree |

Reference data is clean. The mess is confined to `tickets.csv`.

**Fallback join** (`customer_id` + `product_sku`) for the 4,127 tickets with no order_id:
unique match 3,192 · ambiguous (>1 order) 707 · no match 0.
So ~82% resolve uniquely; 18% are genuinely ambiguous. Handling: D-06.

### 6.7 Multiple agent roster assignments — **NOT PRESENT**
The data-pack README warns *"An agent can have more than one row."* In this extract every
agent has exactly one row and every `to_date` is blank. Roster resolution is therefore a
simple lookup — but the code will still implement the date-ranged version so the tool does
not silently break on a future export. Logged D-07.

### 6.8 Timestamp inconsistencies — **TESTED, NO EVIDENCE OF A UTC/IST MIX**

Policy §9 warns that the API exports UTC and that legacy `resolved_at` was reconstructed from
a UTC event log, while the data-pack README says timestamps are IST as displayed.
If legacy `resolved_at` were UTC and `created_at` IST, we would see a −5:30 signature.

| Test | helpdesk | legacy_fd |
|---|---|---|
| Negative `resolved_at − created_at` | 0 | 0 |
| Negative `resolved_at − first_response_at` | 0 | 0 |
| Negative `first_response_at − created_at` | 0 | 0 |
| Median resolution time | 1.83 h | 1.93 h |
| Hour-of-day profile of `resolved_at` | same shape | same shape (peak 12:00–22:00) |
| Timestamps inside the 638 duplicate pairs | identical across both systems | |

**Finding 6.8:** no shift is detectable. All timestamps are treated as IST, as the data-pack
README states. This was a risk we had to rule out, not one we found. Logged D-09.

### 6.9 SLA store credits mixed into refunds — **CANNOT BE SEPARATED**
Policy §3 issues an automatic ₹350 store credit on every first-response breach. If those
credits were written into `refund_amount_inr` they would contaminate the refund total.
Only **18** canonical refunds are exactly ₹350, and they carry ordinary reason codes.
There is no flag, no dedicated code, and breach credits would have to appear on ~all breached
tickets (far more than 18) to be present at all. Conclusion: SLA credits are **not** in this
column. Logged D-11.

### 6.10 Reason-code quality — **THE REAL DATA-QUALITY PROBLEM**

Sameer warned: *"the first option in the list is GW-OTHER… and agents are agents."*

| Reason code | Tickets | Amount | % of value |
|---|---|---|---|
| **GW-OTHER** | 991 | **₹29,07,036** | **43.3%** |
| RETURN-QC-OK | 452 | ₹11,81,386 | 17.6% |
| DUP-PAYMENT | 321 | ₹8,84,586 | 13.2% |
| CANCEL | 222 | ₹6,12,950 | 9.1% |
| DOA-REPL | 147 | ₹4,71,190 | 7.0% |
| WTY-BUYBACK | 89 | ₹2,89,154 | 4.3% |
| PRICE-ADJ | 71 | ₹2,07,073 | 3.1% |
| LOST-TRANSIT | 47 | ₹1,56,557 | 2.3% |
| **Total** | **2,340** | **₹67,09,932** | 100% |

Two hard facts about GW-OTHER:

1. Policy §5 caps goodwill at **₹500 per ticket** with Team Lead approval.
   **879 of 991 GW-OTHER refunds exceed ₹500**, totalling ₹28,71,632. Median ₹2,499, max ₹13,998.
   Either the cap is being breached at scale, or most of these are not goodwill at all.
2. Keyword probes on the free text of GW-OTHER tickets find strong non-goodwill signals:
   payment/duplicate-charge language in 177, return/QC in 181, transit/lost in 143,
   cancellation in 120, warranty in 102.

Worked example — ticket TK-251955, coded GW-OTHER, ₹2,499:
> customer: *"upi shows success, your app shows nothing"*
> agent note: *"payment debited, no ord. chk PG dashboard for txn. Refund approved, Rs 2499"*

That is a textbook DUP-PAYMENT booked as goodwill.

**Finding 6.10:** the single biggest line in Arjun's board pack — "Goodwill / Other, 43% of
refund spend" — is probably not what it says it is. Establishing what it actually is requires
reading 991 free-text pairs. This is the one place an LLM earns its keep, and it is exactly the
"what for" half of the client's question. Deterministic keywords overlap and cannot adjudicate;
an LLM can, and its accuracy is measurable against a hand-labelled sample (Step 4).

### 6.11 Open / pending tickets carrying refunds — **PRESENT, small**
115 canonical refunds (₹3,17,314, 4.7% of value) sit on `open` or `pending` tickets with no
`resolved_at`. Treatment: D-08 / D-10.

### 6.12 Suspicious outliers — **NONE at the value level**
| Test | Result |
|---|---|
| Refund > order value | **0** of 1,542 joinable refunds |
| Refund > 1.5 × order value | 0 |
| Refund / order value ratio | clusters cleanly at 0.10, 0.50, 1.00; max 1.00 |
| Refund > retail price of one unit | 110 — all on multi-unit orders, i.e. legitimate |
| Zero or negative refunds | 0 |
| Non-integer rupee amounts | 0 |

No refund exceeds what the customer paid. Amount-level fraud is not visible in this data.
The anomalies are in **coding and process**, not in the numbers.

### 6.13 Policy contradiction found
Policy §9 states the `transfers` field *"exists only in the current helpdesk"*.
In the data, 340 `legacy_fd` rows have `transfers` > 0. Either the migration backfilled it or
the policy is stale. Impact on refund reporting: none. Logged D-12 for honesty.

## 7. Patterns relevant to "who is giving away money"

Refund rate by first-assigned team (share of that team's tickets that carry a refund):

| Team | Tickets | Refunds | Rate | Refund value |
|---|---|---|---|---|
| Returns Desk | 1,161 | 633 | 54.5% | ₹17,32,192 |
| Billing | 1,600 | 604 | 37.8% | ₹16,01,340 |
| Logistics | 2,054 | 349 | 17.0% | ₹10,87,079 |
| Chat Frontline | 3,229 | 362 | 11.2% | ₹10,93,167 |
| Voice Frontline | 1,000 | 113 | 11.3% | ₹3,42,233 |
| Email Frontline | 1,965 | 204 | 10.4% | ₹5,76,560 |
| Escalations & Warranty | 591 | 75 | 12.7% | ₹2,77,361 |

Policy §6: *"Returns Desk owns return pickups and refund processing; it processes the large
majority of refunds by design."* The top three agents by refund value (A3036 Ritika D'Souza
₹7.74L, A3035 Dev Kulkarni ₹6.28L, A3030 Aishwarya Trivedi ₹5.07L) sit on Returns Desk,
Billing and Logistics — the three teams whose job is refunds.

**Finding 7.1:** naming the highest-rupee agents as "the ones giving away money" would be
wrong and the policy says so in writing. Any agent view must be normalised for exposure and
must show team and tier. Tier 2 agents are explicitly excluded from volume comparison by
policy §6.

**Finding 7.2 (unranked, for Step 3/4):** the more interesting agent-level variable is not
*how much* but *how consistently they reach for GW-OTHER*. GW-OTHER's share of an agent's
refund value ranges from 23.5% to 99.0% across the roster, on comparable work. That range is
too wide to be explained by case mix alone, and it is a coaching question, not an accusation.

## 8. Testing Priya Raman's claim

Priya: *"refunds went up because we told the frontline to stop arguing with customers in Q4.
CSAT went up 0.4 in the same period."*

| Quarter | Tickets | Refund rate | Refund value | Mean CSAT |
|---|---|---|---|---|
| 2025 Q1 | 1,053 | 20.1% | ₹6,09,583 | 3.54 |
| 2025 Q2 | 1,388 | 18.2% | ₹7,27,422 | 3.52 |
| 2025 Q3 | 1,843 | 22.0% | ₹12,07,091 | 3.48 |
| 2025 Q4 | 2,678 | 20.2% | ₹16,27,575 | 3.51 |
| 2026 Q1 | 2,361 | 19.3% | ₹12,58,438 | 3.49 |
| 2026 Q2 | 2,277 | 20.8% | ₹12,79,823 | 3.46 |

**Finding 8.1:** refund **value** did roughly double from Q1 2025 to Q4 2025 — but ticket
**volume** also more than doubled (1,053 → 2,678). The refund **rate** is flat at 18–22%
throughout, with no Q4 step change. And CSAT does not move: it sits at 3.46–3.54 for all six
quarters, a range of 0.08, not the claimed +0.4.

So: refunds went up because contact volume went up. Neither the "agents got generous in Q4"
story nor the "+0.4 CSAT" story is supported by this dataset. This needs to be said carefully
and without blame in the memo — it contradicts the Head of CX on the record.

## 9. What we still do not know

| Unknown | Why it matters | Handling |
|---|---|---|
| Whether a GW-OTHER ticket is *genuinely* goodwill | 43% of refund value | LLM classification with measured accuracy (Step 3–4) |
| Whether refunds on `open`/`pending` tickets are final | ₹3.17L, 4.7% | Reported separately, never silently dropped |
| Why contact volume more than doubled | Drives the whole refund increase | Out of scope; flagged to the client |
| Whether Finance's own export = this `tickets.csv` | Reconciliation assumes so | Stated as an assumption, D-05 |
| True order for 707 ambiguous fallback joins | Context only, never affects a total | Left unresolved and flagged, D-06 |
