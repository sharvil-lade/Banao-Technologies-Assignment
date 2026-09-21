# Final checklist

Every requirement traced from `assignment.txt`, the email thread, and the
five-step build process. Marked **PASS**, **FAIL**, **PARTIAL** or
**NOT IMPLEMENTED**. Nothing is omitted, including the things that did not land.

Verified on a clean machine, 21 September 2026: fresh virtualenv, `pip install -r
requirements.txt`, `python -m vireo.pipeline`, `python -m pytest tests/ -q`.

---

## A. Deliverables named in `assignment.txt`

| # | Requirement | Status | Evidence |
|---|---|---|---|
| A1 | A working AI-assisted tool | **PASS** | `vireo/` (14 modules) + `app/app.py` |
| A2 | Must start from your README on a clean machine | **PASS** | Verified twice in a fresh venv. Only `pandas`, `pytest`, `streamlit`. No key, no database, no Docker. |
| A3 | A business goal, stated as a number | **PASS** | 14.6% → 3.7% of refund spend; ₹1,21,767/qtr; ₹4,87,068/yr. `docs/business-impact.md` |
| A4 | Some way of showing it works | **PASS** | Four layers. 900 field checks, 0 errors; 71 tests; residual ₹0.00. `docs/validation.md` |
| A5 | A one-page memo to Arjun Mehta, non-technical, ≤11 min | **PASS** | `deliverables/memo-arjun-mehta.md` — 1,821 words ≈ **9.1 min** |
| A6 | A screen recording, ≤3 min, no slides | **PARTIAL** | Plan, shot list and timings written (`deliverables/recording-plan.md`). **The recording itself must be captured by the submitter.** |
| A7 | Complete `submission-form.md` | **PASS** | `deliverables/submission-form.md`. File absent from the pack; reconstructed verbatim from `assignment.txt` (D-01). **3 fields need the submitter's own details** and are marked `«FILL IN»`. |

## B. The client's actual ask

| # | Requirement | Status | Evidence |
|---|---|---|---|
| B1 | Monthly refund summary | **PASS** | `monthly_summary.csv`, 18 months; UI *Monthly* tab |
| B2 | By reason code | **PASS** | `by_reason.csv`, `by_reason_month.csv` |
| B3 | By agent | **PASS** | `by_agent.csv` — with exposure, deliberately not ranked (D-15) |
| B4 | "Who, how much, what for" | **PASS** | Who = agent/team with context · How much = reconciled ₹ · What for = recorded code **and** restated from text |
| B5 | "I want the total to reconcile" | **PASS** | Bridge closes at **₹0.00 residual**; 6/6 identities PASS |
| B6 | Droppable into a board pack | **PARTIAL** | Numbers, memo and tables are board-ready. There is one bar chart; no formatted slide export. Deliberate — `docs/scope.md` §9. |
| B7 | Explain the ₹1 cr vs ₹11 L gap | **PASS** | 99.4% legacy paise, 0.5% duplicates. `reports/reconciliation.md` |

## C. Data risks the brief and email thread flagged

| # | Risk | Status | Finding |
|---|---|---|---|
| C1 | Migration duplicates | **PASS** | 638 pairs found, resolved, full audit trail in `duplicate_audit.csv` |
| C2 | Legacy stores money differently | **PASS** | Paise. Measured from 125 pairs, ratio 100.0, std dev 0.0. Re-derived every run. |
| C3 | Refund **and** replacement issued | **PASS** | 202 tickets (166 flagged + 36 text-only). Neha's "one-offs" were understated. |
| C4 | GW-OTHER is the dropdown default | **PASS** | 991 tickets, 43.3% of value; text supports 2.0%. Sameer's warning confirmed. |
| C5 | Missing refund amounts | **PASS** | None. Investigated and ruled out. |
| C6 | Missing reason codes | **PASS** | None — perfectly co-present with amounts. |
| C7 | Invalid foreign keys | **PASS** | Zero orphans on all four joins. |
| C8 | Multiple roster assignments | **PASS** | None in this extract; date-ranged resolution built anyway (D-07) |
| C9 | Timestamp / UTC inconsistency | **PASS** | Tested, no shift detectable. Check runs every execution so a future export fails loudly. |
| C10 | Open / pending tickets | **PASS** | 115 refunds (₹3,17,314) included and flagged, never dropped (D-10) |
| C11 | Suspicious outliers | **PASS** | Zero refunds exceed order value. Anomalies are in coding and process, not amounts. |

## D. The five-step process

| # | Requirement | Status | Evidence |
|---|---|---|---|
| D1 | Step 1 — requirements matrix | **PASS** | `docs/requirements.md` |
| D2 | Step 1 — source-of-truth hierarchy | **PASS** | `docs/decisions.md`, top section |
| D3 | Step 1 — data audit | **PASS** | `docs/data-audit.md` |
| D4 | Step 1 — data risks investigated | **PASS** | Section C above |
| D5 | Step 1 — expected examples defined | **PASS** | `docs/data-dictionary.md` Part 3 — E1–E13, real ticket ids, behaviour not invented numbers |
| D6 | Step 1 — decision log | **PASS** | 17 decisions, each with evidence / choice / reason |
| D7 | Step 1 — four named docs | **PASS** | requirements · data-audit · decisions · data-dictionary |
| D8 | Step 2 — 13 reusable modules | **PASS** | All 13 present; policy-check runs after joins (deviation explained in Step 2 report and `policy.py`) |
| D9 | Step 2 — duplicates not merely dropped | **PASS** | Original ids, status, confidence, chosen/excluded rows, evidence all retained |
| D10 | Step 2 — legacy conversion not assumed | **PASS** | Measured; pipeline aborts if the data stops agreeing |
| D11 | Step 2 — canonical record | **PASS** | 70 columns; `docs/data-dictionary.md` Part 2 |
| D12 | Step 2 — deterministic tests per transformation | **PASS** | 71 tests |
| D13 | Step 2 — `canonical_refunds.csv` | **PASS** | 2,340 rows, ₹67,09,932 |
| D14 | Step 2 — reconciliation report | **PASS** | `reports/reconciliation.md` |
| D15 | Step 3 — monthly summary | **PASS** | total · count · by reason · by agent |
| D16 | Step 3 — agent analysis without labelling agents "bad" | **PASS** | Exposure-adjusted; policy §6 banner in the UI |
| D17 | Step 3 — reason analysis incl. monthly trend | **PASS** | `by_reason_month.csv` |
| D18 | Step 3 — "what for" from free text | **PASS** | `ai_classify.py`; `by_theme.csv` |
| D19 | Step 3 — no LLM arithmetic | **PASS** | Enforced by assertion in `pipeline.py`, tested |
| D20 | Step 3 — suspicious-case detection with evidence links | **PASS** | 958 cases, each with `flag_evidence` |
| D21 | Step 3 — FACT vs INTERPRETATION separated | **PASS** | `ai_*` column prefix; every UI panel labelled |
| D22 | Step 3 — smallest usable reviewer interface | **PASS** | 7 tabs: month, totals, reason drill, agent drill, records, suspicious, reconciliation |
| D23 | Step 4 — deterministic reconciliation | **PASS** | 6 identities, all PASS |
| D24 | Step 4 — sample-based manual validation | **PASS** | 60 records × 15 checks = 900; **0.00% error** |
| D25 | Step 4 — edge-case testing | **PASS** | Table in `docs/validation.md` Layer 3 |
| D26 | Step 4 — AI evaluation with measured accuracy | **PARTIAL** | Tier 1 measured at **97.5%** on 168 labelled tickets. **Tier 2 deliberately unmeasured** — same-model circularity; stated, not hidden, with a costed fix. |
| D27 | Step 4 — business goal found in the data | **PASS** | Five buckets, 888 named tickets, observed / opportunity / target kept apart |
| D28 | Step 4 — scope decisions stated | **PASS** | `docs/scope.md` — 9 exclusions with reasons |
| D29 | Step 5 — README covers all 13 required topics | **PASS** | what · problem · architecture · setup · install · config · run · usage · tests · validation · AI · limitations · assumptions · known issues |
| D30 | Step 5 — final checklist | **PASS** | This file |

## E. Principles the build was held to

| # | Principle | Status | How |
|---|---|---|---|
| E1 | `assignment.txt` takes precedence | **PASS** | Requirements matrix traces every deliverable to a line in it |
| E2 | Provided data is the source of truth | **PASS** | No external data used |
| E3 | Do not fabricate expected values | **PASS** | Step 1 examples define *behaviour*; numeric regressions came from the pipeline afterwards and are labelled as regression guards |
| E4 | Do not assume every row is valid | **PASS** | Validation layer reports, never fixes |
| E5 | Do not silently delete suspicious records | **PASS** | Open tickets kept; excluded duplicates retained in the audit; unknown codes kept |
| E6 | Audit trail of important transformations | **PASS** | `refund_amount_raw`, `conversion_factor`, `duplicate_evidence`, `flag_evidence`, `ai_evidence_quote` |
| E7 | Separate raw / normalised / derived / AI | **PASS** | `data/raw` · in-memory normalised · `data/derived` · `ai_*` columns |
| E8 | Deterministic stays deterministic | **PASS** | Asserted and tested |
| E9 | AI only where it adds value | **PASS** | 5.3% of tickets; free text only |
| E10 | Every business number traceable to source records | **PASS** | UI *Records* tab; `row_hash`; raw amount preserved on every row |
| E11 | Assumptions documented | **PASS** | 17 decisions + README summary table |
| E12 | Limitations documented | **PASS** | `docs/validation.md`, README "Known issues", submission form Q5 |
| E13 | Do not overbuild | **PASS** | No DB, no API, no auth, no CI, one chart |
| E14 | Verify before moving on | **PASS** | Stopped for review after each of the five steps |

---

## Final quality gate — run 21 September 2026

| Gate | Result |
|---|---|
| Clean-machine setup from README alone (fresh venv) | **PASS** |
| Full test suite | **PASS** — 71 passed in 7.97s |
| Data pipeline end to end | **PASS** — 24 tables, 2 reports, ~10s |
| Reconciliation | **PASS** — residual ₹0.00, 6/6 identities |
| Independent recomputation | **PASS** — total and count match |
| Sample verification | **PASS** — 900/900 field checks |
| Application boots | **PASS** — HTTP 200 |
| Final output verification | **PASS** — ₹67,09,932 across 2,340 refunds, 11,600 canonical tickets |

## Outstanding — the honest list

| Item | Status | Owner |
|---|---|---|
| Screen recording capture | **NOT DONE** | Submitter — plan is written |
| Drive link, GitHub URL, honest hours | **NOT DONE** | Submitter — marked `«FILL IN»` |
| Tier-2 AI accuracy measurement | **NOT DONE, by choice** | Needs 50 human-labelled tickets (~1 hr) |
| One real run of the `anthropic` backend | **NOT DONE** | Needs an API key |
| Confirm Finance's export is this file (D-05) | **NOT DONE** | One email to Arjun |
