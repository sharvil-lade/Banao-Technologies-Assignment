# Data Dictionary & Canonical Record Contract

Part 1 documents the data **as received**. Part 2 defines the record the pipeline will
produce. Part 3 is the behavioural contract: named real tickets and the behaviour expected
of each. Part 3 deliberately specifies **behaviour, not expected numbers** — the numbers
come out of the pipeline in Step 2 and are then checked against these rules.

---

# Part 1 — Source columns as received

## `tickets.csv` — 12,238 rows, 21 columns

| Column | Type | Blank | Observed domain | Notes / traps |
|---|---|---|---|---|
| `ticket_id` | string `TK-######` | 0 | TK-240001 … TK-254542 | **Not unique.** 638 ids appear twice. Sequence has 2,942 gaps — normal for an export. |
| `created_at` | datetime `YYYY-MM-DD HH:MM` | 0 | 2025-01-01 → 2026-06-30 | IST (D-09). Always present. |
| `first_response_at` | datetime | 0 | — | Always ≥ `created_at`. 0 violations. |
| `resolved_at` | datetime | 622 | — | Blank ⇔ status `open`/`pending`. Reconstructed from the event log for legacy rows; tested for a UTC shift, none found (D-09). |
| `status` | enum | 0 | resolved 10,518 · closed 1,098 · open 358 · pending 264 | `closed` = auto-closed after 72 h (policy §8), still a completed attendance. |
| `channel` | enum | 0 | chat 5,150 · email 3,883 · voice 1,969 · social 1,236 | Drives contact cost (policy §4). |
| `customer_id` | FK | 0 | 5,221 distinct | 0 orphans. |
| `order_id` | FK | 4,127 (33.7%) | 5,461 distinct | 0 orphans where present. Fallback join is `customer_id`+`product_sku` (D-06). |
| `product_sku` | FK | 0 | 14 | 0 orphans. |
| `category` | enum | 0 | 11 values | Set by the intake bot, may be re-tagged on closure. **Not** a refund reason. |
| `priority` | enum | 0 | Normal 8,689 · High 2,225 · Low 1,324 | |
| `assigned_team` | enum | 0 | 7 teams | **First-routed** team, not necessarily the resolving agent's team. |
| `agent_id` | FK | 0 | 44 | Agent who *resolved*. 0 orphans. Use the id, not the name. |
| `transfers` | int | 0 | 0 · 1 · 2 | Present in legacy rows too, contradicting policy §9 (D-12). ₹305 each (policy §4). |
| `csat_score` | int 1–5 | 6,729 (55.0%) | 1–5 | Blank = no response. **Must be excluded from averages, not zeroed** (policy §8). |
| `refund_amount_inr` | number | 9,773 (79.9%) | see below | **Unit differs by source system.** helpdesk = rupees; legacy_fd = paise (D-03). |
| `refund_reason_code` | enum | 9,773 | 8 codes | Perfectly co-present with the amount. First dropdown option is GW-OTHER. |
| `replacement_issued` | Y/N | 0 | Y 1,347 · N 10,891 | Under-reports: 29 refund tickets say "both" in the note but are flagged N (audit §6.5). |
| `customer_message` | free text | 0 | 11,315 distinct | Opening message, or IVR transcript on voice. Contains typos, shouting, templates. |
| `agent_notes` | free text | 0 | 10,253 distinct | Closing note. Heavy abbreviation (`rfnd`, `rplc`, `cx`, `chk`, `pg`, `wty`). |
| `source_system` | enum | 0 | helpdesk 8,364 · legacy_fd 3,874 | Determines the money unit. |

### `refund_amount_inr` by source system

| | helpdesk | legacy_fd |
|---|---|---|
| Non-blank rows | 1,690 | 775 |
| Min / median / max | 32 / 2,499 / 13,998 | 5,700 / 224,900 / 1,399,800 |
| Divisible by 100 | 5.5% | **100.0%** |
| Unit | rupees | **paise** → ÷100 |

### `refund_reason_code` — from policy §5

| Code | Meaning (policy wording) | Tickets | Value |
|---|---|---|---|
| `GW-OTHER` | Goodwill / Other — **first option in the dropdown**, capped at ₹500 with TL approval | 991 | ₹29,07,036 |
| `RETURN-QC-OK` | Return received and passed QC | 452 | ₹11,81,386 |
| `DUP-PAYMENT` | Duplicate or failed payment | 321 | ₹8,84,586 |
| `CANCEL` | Cancellation before dispatch | 222 | ₹6,12,950 |
| `DOA-REPL` | Dead on arrival, refund chosen | 147 | ₹4,71,190 |
| `WTY-BUYBACK` | Warranty buy-back | 89 | ₹2,89,154 |
| `PRICE-ADJ` | Price or coupon adjustment | 71 | ₹2,07,073 |
| `LOST-TRANSIT` | Lost or undelivered | 47 | ₹1,56,557 |

## `agents.csv` — 44 rows
`agent_id` · `name` · `site` (Bengaluru 24 / Indore 20) · `team` (7) · `shift` (Morning/Day/Night) ·
`tier` (1: 38, 2: 6) · `from_date` · `to_date` (**all blank** = all current).
One row per agent in this extract, though the pack README allows more (D-07).

## `orders.csv` — 15,000 rows
`order_id` · `customer_id` · `sku` · `order_date` · `channel` (Amazon / Flipkart / vireo.in) ·
`qty` · `order_value_inr` · `lot_code`. Fully consistent with tickets on both customer and SKU.

## `customers.csv` — 9,500 rows
`customer_id` · `name` · `city` · `state` · `signup_date` · `care_plus` (Y 2,976 / N 6,524).

## `products.csv` — 14 rows
`sku` · `product_name` · `family` (earbuds / headphones / speaker / watch / accessory) ·
`launch_date` · `unit_cost_inr` (₹90–₹2,650) · `retail_price_inr` (₹399–₹6,999) ·
`warranty_months` (12, or 6 for accessories).
`unit_cost_inr` + ₹340 is the policy replacement cost (policy §5).

---

# Part 2 — Canonical refund record (target schema)

One row per **canonical ticket that carries a refund**. Written to
`data/derived/canonical_refunds.csv`.

### Identity & time
| Field | Source | Notes |
|---|---|---|
| `ticket_id` | raw | **Unique** in this table |
| `month` | `created_at` → `YYYY-MM` | Primary reporting month (D-08) |
| `month_resolved` | `resolved_at` → `YYYY-MM` | Null when open/pending; alternative basis |
| `created_at`, `resolved_at` | raw | IST |

### Who
| Field | Source |
|---|---|
| `agent_id` | raw |
| `agent_name`, `agent_team`, `agent_tier`, `agent_site`, `agent_shift` | roster lookup as of `created_at` (D-07) |
| `assigned_team` | raw — first-routed team, kept distinct from `agent_team` |

### How much
| Field | Notes |
|---|---|
| `refund_amount_inr` | **normalised rupees** — the only field any total may use |
| `refund_amount_raw` | exactly as exported |
| `currency_unit_source` | `INR` \| `paise` |
| `conversion_factor` | 1 \| 100 |

### What for
| Field | Notes |
|---|---|
| `reason_code` | recorded code, **never overwritten** (D-16) |
| `reason_label` | policy §5 wording |
| `ai_suggested_reason` | LLM output, Step 3 |
| `ai_confidence`, `ai_evidence_quote`, `ai_model`, `ai_run_id` | provenance for every AI value |

### Provenance & duplicates
| Field | Notes |
|---|---|
| `source_system` | of the chosen row |
| `duplicate_status` | `unique` \| `canonical_of_pair` |
| `duplicate_partner_source`, `duplicate_partner_amount_raw` | the excluded twin |
| `duplicate_confidence`, `duplicate_evidence` | e.g. `"19/19 business columns identical; amount ratio 100.0"` |

### Context (enrichment only — never affects a total)
`order_id` · `order_match` (`direct` \| `fallback_unique` \| `ambiguous` \| `none`) ·
`order_value_inr` · `order_qty` · `order_channel` · `lot_code` ·
`product_sku` · `product_name` · `product_family` · `unit_cost_inr` · `retail_price_inr` ·
`customer_city` · `customer_state` · `care_plus`

### Policy flags (each with evidence)
| Flag | Rule | Policy |
|---|---|---|
| `flag_refund_and_replacement` | `replacement_issued == Y` and a refund exists | §5 — forbidden |
| `flag_refund_and_replacement_text` | note explicitly states both were given | §5 — forbidden, hidden from the flag |
| `flag_goodwill_over_cap` | `reason_code == GW-OTHER` and amount > ₹500 | §5 — cap |
| `flag_ticket_open` | status in (open, pending) | D-10 |
| `flag_refund_exceeds_order` | amount > `order_value_inr` (direct joins only) | outlier |
| `flag_reason_mismatch` | AI reason ≠ recorded reason at high confidence | interpretation, Step 3 |
| `flag_evidence` | human-readable reason for every flag raised | — |

### Bookkeeping
`row_hash` · `pipeline_version` · `generated_at`

---

# Part 3 — Behavioural contract (expected examples)

Real tickets from the supplied data. Each states the **behaviour** required, not a number
we decided in advance. These become the test cases in Step 2.

### E1 — Normal refund, current helpdesk
**TK-246239** · helpdesk · raw `3058` · RETURN-QC-OK · order VR880597 · A3036, Returns Desk · 2025-10-25
> Passes through unchanged. `conversion_factor = 1`, `refund_amount_inr = refund_amount_raw`.
> `duplicate_status = unique`, `order_match = direct`. No flags. Counted in 2025-10.

### E2 — No refund
**TK-246244** · blank amount, blank reason code
> **Absent** from `canonical_refunds.csv` entirely. Present in the canonical ticket table
> (so denominators for refund *rate* are right). Contributes ₹0.

### E3 — Duplicate ticket, amount present on both sides
**TK-240003** · helpdesk `900` + legacy_fd `90000` · GW-OTHER · A3040
> Exactly **one** output row. Amount **₹900**. `duplicate_status = canonical_of_pair`,
> `duplicate_partner_amount_raw = 90000`, evidence records the 100.0 ratio.
> The legacy row appears in `duplicate_audit.csv`, not in the total.
> **Regression guard:** ₹90,000 must never appear in any output.

### E4 — Duplicate ticket with no money
**TK-240002** · both rows blank amount
> Deduplicated to one canonical ticket; contributes nothing to refunds; must still be
> counted once (not twice) in ticket volume.

### E5 — Legacy-only ticket (migrated, not re-imported)
**TK-240031** · legacy_fd · raw `699900` · DUP-PAYMENT · A3033, Billing · 2025-01-03
> `refund_amount_inr = ₹6,999`, `conversion_factor = 100`, `currency_unit_source = paise`,
> `duplicate_status = unique`. Raw value preserved.

### E6 — Missing order_id
**TK-246285** · no `order_id` · RETURN-QC-OK · ₹5,524 · status **open**
> Refund is **included** (D-10) with `flag_ticket_open = True`.
> Order context resolved by fallback or left empty — either way the ₹5,524 is unaffected.

### E7 — Fallback customer+SKU join, unique
**TK-240009** · no order_id, exactly one matching order for that customer+SKU
> `order_match = fallback_unique`; order context attached; refund total unchanged.

### E8 — Fallback join, ambiguous
**TK-240279** · no order_id, **2** candidate orders
> `order_match = ambiguous`. **No** order attached. No order value invented.
> Refund total unchanged (D-06).

### E9 — Refund **and** replacement (flagged)
**TK-246279** · ₹1,999 · GW-OTHER · `replacement_issued = Y` · A3014, Chat Frontline
> `flag_refund_and_replacement = True`, evidence cites policy §5.
> Amount still counted in the refund total (the money did leave).
> Also carries a modelled replacement cost of `unit_cost + ₹340` in the *impact* view only.

### E10 — Refund + replacement visible only in text
Note reads *"issued refund + replacement both, tl aware"* while `replacement_issued = N`
> `flag_refund_and_replacement_text = True` with the quoted note as evidence.
> Reported **separately** from the flagged 166, because its confidence is lower.

### E11 — Goodwill over the policy cap
**TK-246242** · GW-OTHER · ₹1,400 (> ₹500)
> `flag_goodwill_over_cap = True`, evidence cites policy §5.
> The code is **not** changed and the amount is **not** adjusted.

### E12 — Unknown / invalid reason code
Not present in this dataset (all 8 codes are valid, 0 blanks).
> The loader must still handle it: an unrecognised code maps to `reason_label = "UNKNOWN"`,
> raises `flag_unknown_reason_code`, and the row is **kept**, never dropped.
> Tested with a synthetic fixture, not by editing source data.

### E13 — Reconciliation identity (the client's own test)
> `Σ monthly = Σ by reason code = Σ by agent = canonical total`, to the rupee.
> The bridge `naive raw total → unit correction → duplicate removal → canonical total`
> must close with **zero** unexplained residual.
