**To:** Arjun Mehta, Finance Controller, Vireo Audio
**From:** Kabir Nanda's team
**Date:** 21 September 2026
**Subject:** Refunds — your crore, Sameer's ₹11 lakh, and what is actually happening

---

## The short answer

Sameer's number is right. Yours is the same data read one way that nobody
noticed was wrong.

**Refunds are running at ₹11.2 lakh a quarter, not ₹1 crore-plus.**

Two things inflate the export. Neither is anyone's fault, and neither is fraud.

**1. The old Freshdesk system stored money in paise, not rupees.** A ₹900 refund
is stored as `90000`. Add up the column as exported and every pre-September-2025
refund is counted **one hundred times over**. This accounts for 99.4% of the gap.

We did not assume this — we proved it. During the migration, 638 tickets were
imported twice and appear under both systems. For 125 of them there is a refund
amount recorded by *both*. In **125 cases out of 125**, the old system's number
is exactly 100 times the new one. Not roughly; exactly, every time. And once we
divide by 100, all 125 pairs agree to the rupee.

**2. Those 638 duplicated tickets are being counted twice.** Worth ₹3.6 lakh.

Here is the walk, and it reconciles to the rupee with nothing left over:

| | |
|---|---:|
| Your export, added up as-is | **₹23,01,24,081** |
| less: old-system amounts corrected from paise | −₹22,30,53,138 |
| less: 638 duplicated tickets | −₹3,61,011 |
| **Actual refunds, 18 months** | **₹67,09,932** |
| **Per quarter** | **₹11,18,322** |

**One thing to check on your side.** We assumed the export you added up is the
same file Sameer sent us. If it is, the story above is complete. If you pulled
from somewhere else, tell us and we will redo this — it takes an afternoon.

---

## Refunds went up. Refunding did not.

The rate has not moved:

| Quarter | Tickets | Refunds | **Rate** | CSAT |
|---|---:|---:|---:|---:|
| 2025 Q1 | 1,053 | ₹6.10 L | 20.1% | 3.54 |
| 2025 Q2 | 1,388 | ₹7.27 L | 18.2% | 3.52 |
| 2025 Q3 | 1,843 | ₹12.07 L | 22.0% | 3.48 |
| 2025 Q4 | 2,678 | ₹16.28 L | 20.2% | 3.51 |
| 2026 Q1 | 2,361 | ₹12.58 L | 19.3% | 3.49 |
| 2026 Q2 | 2,277 | ₹12.80 L | 20.8% | 3.46 |

Refund value roughly doubled. So did contacts. Roughly one ticket in five has
ended in a refund for eighteen months straight, with no step change anywhere.

**Refunds went up because contacts went up.** Why contacts more than doubled is
the more valuable question, and nothing in the files you sent can answer it —
it needs sales volume and launch dates. We would start there next.

Two notes on the record, since both were raised in the thread:

- **Priya's Q4 explanation does not show up in the data.** There is no Q4 change
  in the refund rate, and CSAT sits between 3.46 and 3.54 across all six
  quarters — a spread of 0.08, not the +0.4 mentioned. We are not saying the
  policy change didn't happen; we are saying this dataset doesn't show it.
- **Neha's spot check was right, and understated.** More on that below.

---

## "What for" — the part of your board pack that is wrong

Your summary will currently say **Goodwill / Other = 43% of refund spend**.
₹29 lakh over eighteen months, the single biggest line.

It is not true, and Sameer told us why in his first email:

> *"the first option in the list is GW-OTHER (Goodwill / Other) and agents are agents."*

We read the customer message and the closing note on all 991 of those tickets.
**Thirty-seven are actually goodwill.** The rest describe something specific:

| What it is booked as | What the agent's own note says it was | Value |
|---|---|---:|
| Goodwill / Other | Return received, refund chased | ₹9.09 L |
| Goodwill / Other | Warranty fault | ₹5.11 L |
| Goodwill / Other | Duplicate or failed payment | ₹4.90 L |
| Goodwill / Other | Cancellation | ₹3.56 L |
| Goodwill / Other | Lost in transit | ₹2.67 L |
| Goodwill / Other | Damaged on arrival | ₹1.68 L |
| Goodwill / Other | **Genuinely goodwill** | **₹1.36 L** |

One example of the 991, ticket TK-251955. Customer: *"upi shows success, your app
shows nothing."* Agent: *"payment debited, no ord. chk PG dashboard for txn.
Refund approved, Rs 2499."* That is a failed payment. It is booked as goodwill.

**Corrected, the picture is ordinary and much more useful:**

| Reason | As recorded | What it really is |
|---|---:|---:|
| Goodwill / Other | 43.3% | **2.0%** |
| Returns received back | 17.6% | **32.6%** |
| Duplicate / failed payments | 13.2% | **20.5%** |
| Warranty | 4.3% | **16.5%** |
| Cancellations | 9.1% | **14.4%** |

A third of your refunds are ordinary returns. A fifth are payment failures —
money the checkout took for orders it never created, which you then gave back.
Neither is anyone being generous.

**This is a UI problem, not a people problem.** The first option in a dropdown
gets picked. Move `GW-OTHER` off the top of that list and require a reason, and
next quarter's report is right without anybody analysing anything.

---

## Who

We are not giving you a league table, and we would push back if asked for one.

Your own policy (§6) says the Returns Desk *"processes the large majority of
refunds by design"*, and that Tier 2 agents must not be compared with Tier 1 on
volume. The three agents with the largest refund totals sit on Returns Desk,
Billing and Logistics — the three teams whose job is refunds. Ranking them would
be ranking them for doing their jobs.

| Team | Tickets | Refund rate | Refund value |
|---|---:|---:|---:|
| Returns Desk | 1,215 | 50.4% | ₹16.93 L |
| Billing | 1,638 | 36.1% | ₹15.80 L |
| Logistics | 2,073 | 17.2% | ₹11.12 L |
| Chat Frontline | 3,279 | 11.8% | ₹11.65 L |
| Email Frontline | 1,799 | 11.8% | ₹5.64 L |
| Voice Frontline | 870 | 11.3% | ₹2.97 L |
| Escalations & Warranty | 726 | 11.3% | ₹2.99 L |

That is what you would expect. Nothing here suggests an agent problem.

There is one fair comparison, and it is a coaching point rather than a finding:
how often an agent reaches for that default dropdown varies from 24% to 99% of
their refund value, on comparable work. Neha can fix that in a team meeting.

---

## What Neha found, measured

Neha mentioned a couple of tickets where a customer got a refund *and* a
replacement. Your policy (§5) says that must never happen.

**It happened 202 times.** 166 are flagged in the system. Another 36 only show up
in what the agent wrote — notes like *"issued refund + replacement both, TL
aware"* on tickets where the replacement box says No.

It is also increasing: 19, 16, 33, 41, 52, 41 per quarter.

---

## The opportunity: ₹1.22 lakh a quarter

Five specific leaks. Each is a list of tickets you can open by number, not an
estimate. We have been deliberately conservative — where a customer got both a
refund and a replacement, we only count the cheaper of the two, because one of
them was legitimately owed.

| What | Tickets | Per quarter | Realistic saving |
|---|---:|---:|---:|
| Refund **and** replacement on the same order | 202 | ₹59,732 | ₹53,759 |
| Discount that should have applied at checkout, refunded later | 106 | ₹46,238 | ₹32,367 |
| Cost of handling payment failures | 511 | ₹25,631 | ₹17,942 |
| Refund released before the unit was collected | 41 | ₹17,270 | ₹10,362 |
| Goodwill above the ₹500 cap | 28 | ₹14,674 | ₹7,337 |
| **Total** | **888** | **₹1,63,545** | **₹1,21,767** |

**₹1.22 lakh a quarter. ₹4.87 lakh a year.** Avoidable leakage drops from 14.6%
of refund spend to 3.7%.

**What we are not counting, deliberately:** the ₹3.6 lakh a quarter of ordinary
returns (the customer sent the product back — that is not leakage), the ₹1.6
lakh of cancellations (no sale happened), and the ₹2.3 lakh of duplicate-payment
refunds themselves (that is money you should not have taken, returned; only the
cost of handling the contact is a real loss). Counting everything refund-shaped
would have let us claim ₹11 lakh. It would not have survived your first question.

---

## How confident we are

**On the ₹11.2 lakh: very.** It reconciles to the rupee. We recalculated it a
second time with separately written code that shares nothing with the first, and
got the same number. We then re-checked 60 individual refunds against the raw
export across 15 points each — 900 checks, zero errors.

**On the reason codes: confident, and measured.** We checked our reading against
168 tickets we had gone through individually: **97.5% accurate**. The useful
control is that on refunds where the agent picked a *specific* code, we agree
with them 90% of the time. We only disagree where the default was left in place.
That asymmetry is the whole finding.

**Where we are weakest:** about 5% of tickets have notes too terse to read
confidently (*"see prev"*, *"cx ok"*, *"-"*). We handled those separately and
have not claimed an accuracy figure for them, because it would not be an honest
one. If someone on Neha's team spends an hour labelling 50 of them, we can close
that gap properly.

**What we could not do:** explain why contacts doubled. That is the real
question behind your refund increase, and the answer is not in these files.

---

## What we would do next

1. **Move `GW-OTHER` off the top of the dropdown and require a reason.** Free, a
   day of Sameer's time, and it fixes your board pack permanently.
2. **Block refund-plus-replacement on the same order in the helpdesk.** Your
   policy already says it, the system just does not enforce it. ₹53,759 a quarter.
3. **Send the 202 conflict tickets to Neha** — the list is in the tool.
4. **Confirm the export you added up is the file Sameer sent us.** One email.
5. **Get us sales volume and launch dates** if you want the real answer to why
   contacts doubled.

The tool runs in about ten seconds and produces this month's numbers from the
same export. Re-run it next quarter and the same five leaks recalculate
themselves, so you can see whether the fixes worked.

Happy to walk through any number in it before the 24th.
