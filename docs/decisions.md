# Decision Log

Every ambiguity found in Step 1, the evidence consulted, the choice made, and why.
Nothing here is hidden in code. Each decision has a stable ID referenced from the source.

Status key: **LOCKED** = implemented and tested · **OPEN** = deferred to a later step.

---

## Source-of-truth hierarchy (governs every conflict below)

1. **`assignment.txt`** — the brief. Wins over everything.
2. **`email-thread.txt`** — the client's live, dated statements of intent. Wins over static docs
   where the two disagree, because it is later and specific to this engagement.
3. **`support-policy.pdf` v3.2 (eff. 1 Apr 2025)** — authoritative for *rules and definitions*
   (reason codes, cost standards, caps, team ownership).
4. **`README.txt` (data pack)** — authoritative for *column meaning*.
5. **The CSV data itself** — authoritative for *what actually happened*.

**Tie-break rule used throughout:** where a document describes the system and the data
contradicts it, the **data wins for facts** and the **document wins for intent**.
Policy §5 says refund + replacement must never happen; the data says it happened 195 times.
We do not conclude the policy is wrong — we conclude the policy was breached.
Conversely, policy §9 says `transfers` exists only in the current helpdesk; the data shows it
in legacy rows too. That is a factual claim about the data, so the data wins (D-12).

---

## Decisions

### D-01 — `submission-form.md` does not exist in the pack
| | |
|---|---|
| **Evidence** | `assignment.txt` says "Complete `submission-form.md` from this pack." No such file is in the pack (9 files received, listed in `data-audit.md` §1). The questions that would be on it are printed at the end of `assignment.txt`. |
| **Choice** | Reconstruct `deliverables/submission-form.md` using those trailing questions **verbatim, in order**. |
| **Reason** | The requirement is to answer the questions, not to possess the file. Inventing extra questions would be scope creep; skipping the deliverable would be an incomplete submission. |
| **Status** | LOCKED |

### D-02 — Duplicate resolution: keep the `helpdesk` row
| | |
|---|---|
| **Evidence** | 638 pairs, all `helpdesk`+`legacy_fd`, identical on all 19 business columns except `refund_amount_inr` (differs on 125). All pre-date the 14 Sep 2025 go-live. Policy §9 documents the re-import. Helpdesk stores rupees; legacy stores paise. |
| **Choice** | Where a `ticket_id` appears twice, the **`helpdesk` row is canonical**. The `legacy_fd` twin is marked `excluded_duplicate`, retained in full in `data/derived/duplicate_audit.csv` with both amounts, the ratio, and the reason. |
| **Reason** | The current system is the system of record and stores money in the reporting currency. Choosing it needs no conversion, so it introduces no new error. Critically, the rows are otherwise identical, so the choice cannot change any non-money field. |
| **Rejected** | (a) Dropping both — loses 638 real tickets. (b) Keeping legacy — requires converting 638 more amounts for no gain. (c) `drop_duplicates()` on the whole row — would silently keep 125 wrong amounts, because those rows are *not* identical. |
| **Status** | LOCKED |

### D-03 — Legacy monetary unit is paise (÷100)
| | |
|---|---|
| **Evidence** | 125 duplicate pairs carry an amount on both sides. `legacy ÷ helpdesk = 100.0` in **125 of 125** cases, standard deviation **0.0**. 775 of 775 legacy amounts are divisible by 100; only 5.5% of helpdesk amounts are. Legacy median ÷100 = ₹2,249 vs helpdesk median ₹2,499 — same order as retail prices in `products.csv` (₹399–₹6,999). Policy §9 confirms a different native unit but does not name it. |
| **Choice** | `legacy_fd` amounts are divided by 100. Applied **only** to `refund_amount_inr`, and **only** to rows tagged `legacy_fd`. |
| **Reason** | 125 zero-variance paired observations is direct measurement, not inference. Paise is also the standard Indian minor unit and the standard Freshdesk storage convention. |
| **Residual risk** | The 125 pairs all fall in Jan–Sep 2025. If the legacy unit had changed earlier in that window we could not see it. Mitigation: divisibility-by-100 holds for **all** 775 legacy amounts across the whole legacy period, not just the paired ones. We judge the residual risk low and state it rather than hide it. |
| **Isolation** | Every converted row keeps `refund_amount_raw`, `currency_unit_source` and `conversion_factor` so any reviewer can undo it. |
| **Status** | LOCKED |

### D-04 — The reconciliation target is ~₹11.18 lakh/quarter, not ₹1 crore
| | |
|---|---|
| **Evidence** | Bridge in `data-audit.md` §5: naive ₹23.01 cr → unit fix → ₹70.71 L → dedup → ₹67.10 L over 18 months = ₹11.18 L/quarter. Sameer's helpdesk report says "around Rs 11 lakh a quarter". |
| **Choice** | Report the canonical figure as correct and present the bridge as the primary answer to Arjun's "I want the total to reconcile". |
| **Reason** | Two independent client numbers exist; one is reproducible from the data by a known error and one is reproducible from the data by correct handling. We show the arithmetic for both rather than asserting a winner. |
| **Status** | LOCKED |

### D-05 — Assume Finance's export is this `tickets.csv`
| | |
|---|---|
| **Evidence** | We were given one ticket export. Arjun's figure is reproducible from it by a single unit error. |
| **Choice** | Assume Arjun's crore comes from this export mishandled, not from a different file. |
| **Reason** | The naive sum lands in his stated range, which would be a large coincidence otherwise. |
| **Limitation** | We cannot prove it. **Stated explicitly in the memo** as the one thing Arjun should confirm on his side. |
| **Status** | LOCKED, flagged as an assumption |

### D-06 — Ambiguous fallback joins are left unresolved
| | |
|---|---|
| **Evidence** | 4,127 tickets have no `order_id`. The documented fallback (`customer_id` + `product_sku`) gives a unique order for 3,192 and **multiple** candidates for 707. Zero tickets match nothing. |
| **Choice** | Attach order context only where the match is unique. For the 707, set `order_match = 'ambiguous'`, attach nothing, and record the candidate count. Order data is **enrichment only** — it never enters a refund total. |
| **Reason** | Picking "the most recent order" would be a fabricated rule. Since no reported number depends on the order join, ambiguity costs us context but never correctness. |
| **Status** | LOCKED |

### D-07 — Date-ranged roster lookup, even though it is not needed here
| | |
|---|---|
| **Evidence** | Data-pack README: "An agent can have more than one row." In this extract all 44 agents have exactly one row and every `to_date` is blank. |
| **Choice** | Implement `resolve_agent(agent_id, as_of_date)` with from/to date filtering; add a test that proves it picks the right row when several exist. |
| **Reason** | Costs ~15 lines. Without it the tool silently returns duplicated rows on the next export that has a transfer in it. This is the one place we build slightly beyond today's data, and we say so. |
| **Status** | LOCKED |

### D-08 — Refunds are attributed to the **created_at** month
| | |
|---|---|
| **Evidence** | The refund raise time is not stored. Candidates are `created_at` (always present) and `resolved_at` (blank on 115 refund tickets, 4.7% of value). Only **80 of 2,340** refund tickets (3.4%) cross a month boundary between the two, so the choice moves very little money. |
| **Choice** | Month = month of `created_at`. |
| **Reason** | It is present on 100% of rows, so no refund is ever dropped from the monthly series, and the series never changes retrospectively as open tickets close. |
| **Trade-off, stated** | This is a *ticket-cohort* view, not a *cash-out* view. Finance may want the accounting month. The pipeline therefore also emits `month_resolved`, and the UI has a toggle. The default is documented in the memo so Arjun is not surprised. |
| **Status** | LOCKED |

### D-09 — All timestamps treated as IST
| | |
|---|---|
| **Evidence** | Policy §9 warns of a UTC/IST mix (API exports UTC; legacy `resolved_at` reconstructed from a UTC event log). Data-pack README says timestamps are IST as displayed. Tests: 0 negative durations of any kind in either system; identical hour-of-day profiles; identical timestamps inside all 638 duplicate pairs; median resolution 1.83 h vs 1.93 h. A 5.5-hour shift would be unmissable. |
| **Choice** | Treat all timestamps as IST. No conversion applied. |
| **Reason** | The warning describes the API and the event log; this export is the *standard report*, which policy §9 says displays IST. The data agrees. Applying an unnecessary correction would create the error we were trying to avoid. |
| **Status** | LOCKED — and recorded as a **test that was run**, not an assumption |

### D-10 — Refunds on open/pending tickets are included, and flagged
| | |
|---|---|
| **Evidence** | 115 refunds (₹3,17,314) sit on `open`/`pending` tickets. A refund amount is recorded, so money was raised. |
| **Choice** | Include in the canonical total; set `ticket_open = True`; show as a separate line in the reconciliation and a filter in the UI. |
| **Reason** | Principle: do not silently delete suspicious records. Excluding them would understate refunds by 4.7% with no evidence that they were reversed. |
| **Status** | LOCKED |

### D-11 — SLA breach credits are not in `refund_amount_inr`
| | |
|---|---|
| **Evidence** | Policy §3: automatic ₹350 store credit on every first-response breach, charged to a separate SLA credit line. Only 18 canonical refunds equal exactly ₹350, and they carry ordinary reason codes. Breach volume is far higher than 18. |
| **Choice** | Treat `refund_amount_inr` as refunds only. Do not attempt to strip SLA credits. |
| **Reason** | If credits were in this column there would be hundreds of ₹350 rows. There are 18, consistent with ordinary small refunds. There is no defensible rule to remove them and removing 18 arbitrary rows would be worse than keeping them. |
| **Status** | LOCKED |

### D-12 — `transfers` in legacy rows contradicts policy §9
| | |
|---|---|
| **Evidence** | Policy §9: the field "exists only in the current helpdesk". Data: 340 `legacy_fd` rows have `transfers` > 0. |
| **Choice** | Use the data. Do not null out legacy `transfers`. Record the contradiction. |
| **Reason** | Factual claim about the data → data wins. Zero impact on refund reporting; logged only so nobody later finds it and assumes we missed it. |
| **Status** | LOCKED |

### D-13 — "Some way of showing it works" = four layers
| | |
|---|---|
| **Evidence** | `assignment.txt`: "We are not telling you what shape this takes." Arjun: "I want the total to reconcile." |
| **Choice** | (1) Reconciliation bridge with zero residual; (2) deterministic unit tests per transformation; (3) hand-checked random sample of canonical records with a stated error rate; (4) a hand-labelled evaluation set for the AI classifier with measured accuracy. |
| **Reason** | The client's own test is reconciliation, so that leads. The other three cover what reconciliation cannot catch: a total can reconcile perfectly and still be built from wrong rows. |
| **Status** | OPEN — built in Steps 2 and 4 |

### D-14 — Stack: Python + pandas + Streamlit; LLM for free text only
| | |
|---|---|
| **Evidence** | "Any stack, any models"; 5-hour cap; "a small thing that runs beats a large thing that does not". |
| **Choice** | pandas pipeline → `canonical_refunds.csv` → Streamlit single-file reviewer UI. LLM used **only** to interpret `customer_message` / `agent_notes`. Its output lands in columns prefixed `ai_` and is never summed into a financial total. |
| **Reason** | Every number must be reproducible without a network call. Separating `ai_*` columns makes the FACT / INTERPRETATION boundary structural rather than a matter of discipline. |
| **Status** | OPEN — built in Steps 2 and 3 |

### D-15 — Agents are not ranked by refund rupees alone
| | |
|---|---|
| **Evidence** | Policy §6: Returns Desk "processes the large majority of refunds by design"; Tier 2 agents "are not to be compared with Tier 1 on volume metrics". Data: the top three agents by refund value all sit on refund-owning teams. Priya Raman has already objected to agents being blamed. |
| **Choice** | Every agent view shows team, tier, ticket volume and refund rate alongside rupees. Tier 2 is separated, never pooled with Tier 1. No "worst agent" ranking is produced. |
| **Reason** | The client asked "who is giving away money", and the honest answer is that the highest-rupee agents are the people whose job is refunds. Handing Arjun a raw league table would be the single most damaging thing this tool could do, and the policy says so in writing. |
| **Status** | LOCKED — this is a deliberate narrowing of the client's ask, reported in the submission form |

### D-16 — GW-OTHER re-classification is an interpretation, never a restatement
| | |
|---|---|
| **Evidence** | 991 GW-OTHER refunds, ₹29.07 L, 43.3% of value. 879 exceed the ₹500 policy cap. Free text on many clearly describes a different, specific reason. |
| **Choice** | Never overwrite `refund_reason_code`. Add `ai_suggested_reason`, `ai_confidence` and `ai_evidence_quote` beside it. Headline totals always use the **recorded** code. The re-classified view is presented as a separate, labelled "what the text says" panel. |
| **Reason** | The recorded code is what the source system says and Arjun's board pack must tie to it. The AI view answers "what for" without corrupting "how much". |
| **Status** | OPEN — built in Step 3, measured in Step 4 |

### D-17 — Source pack copied, never modified
| | |
|---|---|
| **Evidence** | Working instruction: "Do not modify the source files." |
| **Choice** | Originals stay untouched in `docs/` exactly as received. Byte-identical copies with readable names live in `data/raw/` and are what the pipeline reads. |
| **Reason** | A clean machine needs predictable filenames; the originals carry upload UUIDs. Copying preserves both. |
| **Status** | LOCKED |
