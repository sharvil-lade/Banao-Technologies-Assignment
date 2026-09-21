# Vireo Audio — Refund Analysis Pipeline

A deterministic pipeline that reconciles Vireo Audio's messy support-ticket
export into an auditable monthly refund summary, plus an AI-assisted layer
that explains *why* refunds happen — kept strictly separate from the numbers.

**Headline result:** Finance's export sums to ~₹2.3 crore. The true figure is
**₹11,18,322 per quarter** (₹67,09,932 over 18 months). The gap is a unit bug
(the legacy system stored paise, not rupees) plus 638 duplicate rows from a
data migration — both proven from the data, with zero unexplained residual.

## Table of Contents

- [Quick Start](#quick-start)
- [What This Does](#what-this-does)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Testing](#testing)
- [How It Works](#how-it-works)
- [AI Usage & Cost](#ai-usage--cost)
- [Validation](#validation)
- [Key Finding](#key-finding)
- [Assumptions](#assumptions)
- [Known Limitations](#known-limitations)
- [Documentation](#documentation)

## Quick Start

Requires **Python 3.10+**. No database, no Docker, no API key.

```bash
git clone <this-repo>
cd ass1
pip install -r requirements.txt

python -m vireo.pipeline      # run the full pipeline (~10s)
python -m pytest -q            # run the test suite (71 tests, ~9s)
python -m streamlit run app/app.py   # open the reviewer UI at http://localhost:8501
```

Expected pipeline output ends with:

```
[9/9] reconciled  residual=Rs 0.00 identities=ALL PASS
```

If the residual isn't ₹0.00, the pipeline refuses to write output — that's
deliberate, not a bug.

<details>
<summary>Using a virtual environment (optional)</summary>

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Verified from scratch in a clean virtualenv: `pandas`, `pytest`, `streamlit`
install and the full pipeline runs with no other setup.
</details>

## What This Does

Arjun Mehta (Finance Controller) needed a monthly refund summary by reason
code and by agent, board-pack ready — but the two internal reports of "total
refunds" disagreed by ~100×, and he trusted neither.

This pipeline:

1. **Reconciles** the numbers to zero unexplained residual, every adjustment
   traced to a cause.
2. **Classifies** *why* each refund happened from free-text agent notes and
   customer messages — deterministic rules first, a model only for the ~5%
   rules can't resolve.
3. **Never lets AI touch a number.** The model reads text and returns a
   label; every rupee is computed by pandas. Enforced by an assertion, not a
   convention.
4. **Quantifies avoidable spend** into named, non-overlapping buckets with a
   stated reduction target.

## Usage

**"What did we refund in March 2026, and what for?"**
Open the app → pick `2026-03` → *Monthly* shows ₹4,35,773 across 163 refunds
(19.5% of tickets). *Reason codes* breaks it down as recorded. *What for
(AI)* shows what the free text actually says.

**"Show me ticket TK-240003, I don't believe the number."**
*Records* tab → pick the ticket. Left panel is FACT (₹900, exported as
90,000 paise, factor 100, helpdesk row of a migration pair). Right panel is
INTERPRETATION (the model's reading + quoted evidence). Below that: the
customer message, the agent's note, and the duplicate-audit row showing the
excluded twin and why.

**"Prove the ₹11 lakh."**
*Reconciliation* tab, or [`reports/reconciliation.md`](reports/reconciliation.md).

**From the command line:**

```bash
python -c "
import pandas as pd
r = pd.read_csv('data/derived/canonical_refunds.csv')
print(r.groupby('month').refund_amount_inr.sum().round(0))"
```

## Project Structure

```
vireo/            pipeline modules: load → validate → normalise → dedupe →
                  joins → agents → policy → canonical → aggregate →
                  ai_classify → reconcile → impact → validate_sample → costs
tests/            71 tests
app/app.py        Streamlit reviewer UI
scripts/          one-off Step 1 data-audit scripts (not part of the
                  pipeline; see scripts/README.md)
prompts/          the AI classifier prompt, versioned
data/raw/         supplied files, unmodified
data/derived/     24 generated tables (canonical_refunds.csv is the key one)
data/eval/        168-ticket gold label set
data/ai_labels/   tier-2 label cache (lets a clean machine reproduce the numbers)
reports/          reconciliation.md · validation.md
docs/             requirements, data audit, decisions, data dictionary,
                  AI design, validation, business impact, scope, checklist
deliverables/     memo to Arjun Mehta, submission form, recording plan
```

**Three things worth knowing before you touch the code:**

1. `canonical_refunds.csv` is the only table any total may come from. One
   row per ticket, amounts already in rupees.
2. `reason_code` is a fact; `ai_suggested_reason` is an opinion. The second
   never overwrites the first — the pipeline asserts the AI layer cannot
   change a refund total.
3. The ÷100 conversion factor is measured, not configured.
   `verify_legacy_conversion()` re-derives it every run and aborts on
   disagreement.

## Configuration

Everything tunable lives in `vireo/config.py`, each value traced to a source:

| Setting | Value | Source |
|---|---|---|
| `LEGACY_CONVERSION_FACTOR` | 100 | Measured from 125 duplicate pairs (D-03); re-derived every run |
| `GOODWILL_CAP_INR` | 500 | policy §5 |
| `REPLACEMENT_LOGISTICS_INR` | 340 | policy §5 |
| `CONTACT_COST_INR` | chat 210 · email 260 · voice 520 · social 240 | policy §4 |
| `TRANSFER_COST_INR` | 305 | policy §4 |
| `SOURCE_PRIORITY` | helpdesk wins a duplicate pair | D-02 |

The AI backend is also configurable from the command line:

```bash
python -m vireo.pipeline                        # two_tier (default), no key needed
python -m vireo.pipeline --ai-backend rules      # keyword baseline, no model at all
python -m vireo.pipeline --ai-backend cache      # reload the last run's labels, no key
python -m vireo.pipeline --help                  # full list of flags
```

See [AI Usage & Cost](#ai-usage--cost) for running it against a live model.

## Testing

```bash
python -m pytest -q        # 71 tests, ~9 seconds
```

Covers duplicate handling, the legacy unit, missing values, joins, roster
resolution, refund+replacement conflicts, monthly aggregation, the impact
model, and the invariant that the AI layer cannot change a refund total. One
test demonstrates that a naive `drop_duplicates()` would have banked
₹90,000 where the truth is ₹900.

## How It Works

```
data/raw/*.csv                     supplied files, never modified
     │
     ▼
 load  ──►  validate  ──►  normalise  ──►  dedupe  ──►  joins  ──►  agents
                              │              │
                   legacy paise ÷ 100   638 pairs, helpdesk row wins,
                   (factor re-derived   excluded twin kept in the audit
                    from the data)
     │
     ▼
  policy flags  ──►  canonical_refunds.csv   ◄── the only table totals come from
     │
     ├──► aggregate       monthly · by reason · by agent · by team   DETERMINISTIC
     ├──► ai_classify     tier 1 rules (94.7%) → tier 2 model (5.3%) INTERPRETATION
     ├──► reconcile       bridge + 6 identities, residual must be ₹0
     ├──► impact          5 mutually-exclusive avoidable-cost buckets
     └──► validate_sample independent re-derivation, shares no code
     │
     ▼
 data/derived/*.csv  ·  reports/*.md  ·  app/app.py (Streamlit reviewer)
```

The one rule the whole design enforces: every rupee is computed by pandas.
The model reads free text and returns a *label*, never a number — the
pipeline asserts this and aborts if it's ever untrue.

## AI Usage & Cost

Full detail in [`docs/ai-design.md`](docs/ai-design.md).

Two tiers. Deterministic rules resolve **94.7%** of refunds for free; only
the **5.3%** that are genuinely ambiguous reach a model.

| | One full run (18 months) | Per month at 650 tickets/week |
|---|---:|---:|
| Model calls | 125 | **30** |
| Cost (Claude Haiku 4.5) | ₹3.38 | **₹0.81** |
| Cost (Claude Sonnet 4.5) | ₹10.14 | ₹2.44 |
| Same job, everything to the model | — | ₹46.11 |

### Running it against the live API

```bash
cp .env.example .env        # then edit .env and paste in ANTHROPIC_API_KEY
pip install anthropic       # not in requirements.txt by default
python -m vireo.pipeline --escalate-backend anthropic
```

`.env` is gitignored and loaded automatically via `python-dotenv` — nothing
to `export` by hand. Leave `--ai-backend` at its default (`two_tier`): rules
still resolve 94.7% of refunds for free, and only the ~125 escalated tickets
call the model — the whole point of the two-tier design. `--ai-backend
anthropic` also works but sends all 2,340 refunds to the model, the "naive"
baseline this design exists to avoid.

## Validation

Four layers. Full detail in [`docs/validation.md`](docs/validation.md).

| Layer | Result |
|---|---|
| Reconciliation bridge | residual **₹0.00**; 6/6 identities PASS |
| Conversion factor re-derived from data | 125/125 pairs, ratio 100.0, std dev 0.0 |
| Independent recomputation (stdlib only, shares no code) | total and count **PASS** |
| 60-record sample × 15 checks = **900 field checks** | **0 failures, 0.00% error rate** |
| Edge-case tests | **71 passing** |
| AI tier-1 accuracy vs 168-ticket gold set | **97.5%** |
| Control: agreement with recorded code on non-GW refunds | **90.4%** |

## Key Finding

**Of 991 refunds booked as "Goodwill / Other" (₹29,07,036, 43.3% of refund
value), the free text supports genuine goodwill on 37 (₹1,35,652, 2.0%).**

| Reason | As recorded | As the text reads |
|---|---:|---:|
| Goodwill / Other | **43.3%** | **2.0%** |
| Return received & QC'd | 17.6% | 32.6% |
| Duplicate/failed payment | 13.2% | 20.5% |
| Warranty buy-back | 4.3% | 16.5% |
| Cancellation | 9.1% | 14.4% |

**Business goal:** cut avoidable refund leakage from **14.6% → 3.7%** of
refund spend — **₹1.22 lakh a quarter, ₹4.87 lakh a year**. Five named
buckets, 888 tickets you can open individually. See
[`docs/business-impact.md`](docs/business-impact.md).

## Assumptions

Full log with evidence in [`docs/decisions.md`](docs/decisions.md) — 17
decisions. The ones that move numbers:

| ID | Assumption | Basis |
|---|---|---|
| D-03 | Legacy Freshdesk amounts are paise | 125 paired observations, ratio 100.0, zero variance — **measured, not assumed** |
| D-02 | The helpdesk row wins a duplicate pair | It is the system of record and already stores rupees |
| D-05 | Finance's ₹1 crore comes from **this** export | Reproducible from it by one unit error — **unproven**, the one thing to confirm with Arjun |
| D-08 | Month = `created_at` month | Present on 100% of rows; only 3.4% of refunds fall in a different month otherwise |
| D-10 | Refunds on open/pending tickets count | ₹3,17,314 (4.7%); included and flagged, never silently dropped |
| D-09 | All timestamps are IST | Tested for a UTC shift; zero negative durations in either system |

## Known Limitations

Fuller version in [`docs/validation.md`](docs/validation.md), "What we know
is wrong".

1. **Tier-2 AI accuracy is unmeasured.** Its labels and the gold set came
   from the same model, so measuring one against the other would be
   circular. Affects 5.3% of refunds. Fix: hand-label 50 tickets (~1 hour).
2. **The `anthropic` backend has never been executed** — no API key in the
   build environment. Code is written and reviewed; it needs one real run.
3. **707 refund tickets have an ambiguous order join.** Deliberately
   unresolved (D-06); a test asserts no total depends on it.
4. **Replacement-conflict detection in free text is high-precision,
   low-recall.** The true conflict count is ≥ 202. Under-counting is the
   safe direction for a claim.
5. **The ÷100 evidence comes from pairs dated Jan–Sep 2025 only,** mitigated
   by divisibility-by-100 holding for all 775 legacy amounts.
6. **No root cause for the volume increase.** Tickets more than doubled,
   which — not agent generosity — is what drove refunds up. Flagged as the
   next question.

## Documentation

| Doc | Contents |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | Requirements matrix, source-of-truth hierarchy |
| [`docs/data-audit.md`](docs/data-audit.md) | Full data profiling and risk log |
| [`docs/decisions.md`](docs/decisions.md) | 17 decisions, each with evidence |
| [`docs/data-dictionary.md`](docs/data-dictionary.md) | Column reference + 13 behavioral examples |
| [`docs/ai-design.md`](docs/ai-design.md) | AI architecture, cost, and the same-model-circularity disclosure |
| [`docs/validation.md`](docs/validation.md) | All four validation layers in detail |
| [`docs/business-impact.md`](docs/business-impact.md) | Observed / opportunity / target breakdown |
| [`docs/scope.md`](docs/scope.md) | What was deliberately left out, and why |
| [`docs/final-checklist.md`](docs/final-checklist.md) | Every requirement, PASS/FAIL/NOT IMPLEMENTED |
| [`deliverables/memo-arjun-mehta.md`](deliverables/memo-arjun-mehta.md) | The one-page memo to Finance |
