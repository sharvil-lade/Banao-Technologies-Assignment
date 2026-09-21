# Vireo Audio — monthly refund analysis

A small, auditable tool that turns Vireo's messy helpdesk export into a monthly
refund summary Finance can put in a board pack — and shows its working.

**The short version:** Finance's export sums to over ₹1 crore a quarter. The
helpdesk report says about ₹11 lakh. The helpdesk is right. The entire gap is a
unit error (legacy Freshdesk stored paise) plus 638 duplicate rows from a
migration re-import. The reconciled figure is **₹11,18,322 per quarter**, and
this repo walks from one number to the other with **zero unexplained residual**.

---

## The business problem

Arjun Mehta, Finance Controller:

> *"Refunds have gone up and I can't see why. I need a monthly summary of refunds
> by reason code and by agent — who is giving away money and for what. Something
> I can drop straight into the board pack. The helpdesk export is a mess."*

Three things had to be true before that summary was worth printing:

1. **The total has to reconcile.** Two client figures differed by ~100×.
2. **"For what" has to be real.** 43% of refund value is booked to `GW-OTHER`,
   which is the first option in the agent's dropdown. The free text supports
   genuine goodwill on **2%**.
3. **"Who" must not become a league table.** Policy §6 says the Returns Desk
   processes most refunds *by design*. The highest-rupee agents are the people
   whose job is refunds.

---

## Architecture

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
     ├──► aggregate   monthly · by reason · by agent · by team      DETERMINISTIC
     ├──► ai_classify tier 1 rules (94.7%) → tier 2 model (5.3%)    INTERPRETATION
     ├──► reconcile   bridge + 6 identities, residual must be ₹0
     ├──► impact      5 mutually-exclusive avoidable-cost buckets
     └──► validate_sample   independent re-derivation, shares no code
     │
     ▼
 data/derived/*.csv  ·  reports/*.md  ·  app/app.py (Streamlit reviewer)
```

**The one rule the whole design enforces:** every rupee is computed by pandas.
The model reads free text and returns a *label*, never a number. The pipeline
asserts this and aborts if it is ever untrue.

---

## Setup

Requires **Python 3.10+**. Nothing else — no database, no Docker, no API key.

```bash
git clone <this-repo>
cd ass1

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`make setup` does the same three commands. `pip install -e ".[dev]"` also
works, via `pyproject.toml`, if you'd rather install the package properly.

Verified from scratch in a clean virtualenv on 2026-09-21: `pandas`, `pytest`,
`streamlit` install and the full pipeline runs with no other setup.

---

## How to run

```bash
python -m vireo.pipeline          # the whole thing, ~10 seconds
```

Expected output:

```
[1/9] loaded      tickets=12,238 agents=44 orders=15,000 customers=9,500 products=14
[2/9] validated   errors=0 issues=9
[3/9] normalised  legacy factor re-measured from data: 100.0 (125 pairs, unanimous=True)
[4/9] deduplicated pairs=638 excluded_rows=638 canonical_tickets=11,600
[5/9] roster      {'in_force': 11600}
[6/9] joined      {'direct': 7701, 'fallback_unique': 3192, 'ambiguous': 707}
[7/9] policy      refunds=2,340 total=Rs 6,709,932 suspicious=958
[7b/9] ai         tier1(rules,free)=2,215 tier2(model)=125 (5.3% escalated) reason_mismatch=1,084
[8/9] aggregated  months=18 reasons=8 agents=44
[9/9] reconciled  residual=Rs 0.00 identities=ALL PASS
[10/10] verified   sample=60 rows, 900 field checks, error rate 0.0% | ...
```

If the residual is not ₹0.00, or any identity fails, **the pipeline refuses to
write output**. That is deliberate.

Then the reviewer UI:

```bash
streamlit run app/app.py          # http://localhost:8501
```

---

## Sample usage

**"What did we refund in March 2026, and what for?"**
Open the app → pick `2026-03` → *Monthly* shows ₹4,35,773 across 163 refunds
(19.5% of tickets). *Reason codes* breaks it down as recorded. *What for (AI)*
shows what the free text actually says.

**"Show me ticket TK-240003, I don't believe the number."**
*Records* tab → pick the ticket → left panel is FACT (₹900, exported as 90000
paise, factor 100, helpdesk row of a migration pair), right panel is
INTERPRETATION (the model's reading + quoted evidence), below that the customer
message, the agent's note, and the duplicate-audit row showing the twin that was
excluded and why.

**"Prove the ₹11 lakh."**
*Reconciliation* tab, or `reports/reconciliation.md`.

**Command line:**
```bash
python -c "
import pandas as pd
r = pd.read_csv('data/derived/canonical_refunds.csv')
print(r.groupby('month').refund_amount_inr.sum().round(0))"
```

---

## Configuration

Everything tunable lives in `vireo/config.py`, each value traced to a source:

| Setting | Value | Source |
|---|---|---|
| `LEGACY_CONVERSION_FACTOR` | 100 | Measured from 125 duplicate pairs (D-03). Re-derived every run; the pipeline aborts if the data stops agreeing. |
| `GOODWILL_CAP_INR` | 500 | policy §5 |
| `REPLACEMENT_LOGISTICS_INR` | 340 | policy §5 |
| `CONTACT_COST_INR` | chat 210 · email 260 · voice 520 · social 240 | policy §4 |
| `TRANSFER_COST_INR` | 305 | policy §4 |
| `SOURCE_PRIORITY` | helpdesk wins a duplicate pair | D-02 |

AI backend (default needs no key - see "AI usage" below for the live-API setup):

```bash
python -m vireo.pipeline                        # two_tier (default), no key needed
python -m vireo.pipeline --ai-backend rules      # keyword baseline, no model at all
python -m vireo.pipeline --ai-backend cache      # reload the last run's labels, no key
python -m vireo.pipeline --help                  # full list of flags
```

---

## Tests

```bash
python -m pytest tests/ -q        # 71 tests, ~6 seconds
```

Covers duplicate handling, the legacy unit, missing values, joins, roster
resolution, refund+replacement conflicts, monthly aggregation, the impact model,
and the invariant that the AI layer cannot change a refund total. One test
demonstrates that a naive `drop_duplicates()` would have banked ₹90,000 where
the truth is ₹900.

---

## Validation — how we know it works

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

---

## AI usage

Full detail in [`docs/ai-design.md`](docs/ai-design.md).

Two tiers. Deterministic rules resolve **94.7%** of refunds for nothing; only the
**5.3%** that are genuinely ambiguous reach a model.

| | One full run (18 months) | Per month at 650 tickets/week |
|---|---:|---:|
| Model calls | 125 | **30** |
| Cost (Claude Haiku 4.5) | ₹3.38 | **₹0.81** |
| Cost (Claude Sonnet 4.5) | ₹10.14 | ₹2.44 |
| Same job, everything to the model | — | ₹46.11 |

The model never sees a number it is asked to add. Its output lands in `ai_*`
columns and never overwrites the recorded `reason_code`. The UI labels every
panel **FACT** or **INTERPRETATION**.

**Running it against the live API instead of the shipped cache:**

```bash
cp .env.example .env        # then edit .env and paste in ANTHROPIC_API_KEY
pip install anthropic       # not in requirements.txt by default - see below
python -m vireo.pipeline --escalate-backend anthropic
```

`.env` is gitignored and loaded automatically (via `python-dotenv`) - nothing
to `export` by hand. Leave `--ai-backend` at its default (`two_tier`): rules
still resolve 94.7% of refunds for free, and only the ~125 escalated tickets
actually call the model, which is the whole point of the two-tier design
above. `--ai-backend anthropic` also works but sends all 2,340 refunds to the
model - the "naive" baseline this design was built to avoid, kept only so the
full-API path is honest and complete rather than silently unsupported.

---

## The finding

**Of 991 refunds booked as "Goodwill / Other" (₹29,07,036, 43.3% of refund
value), the free text supports genuine goodwill on 37 (₹1,35,652, 2.0%).**

| Reason | As recorded | As the text reads |
|---|---:|---:|
| Goodwill / Other | **43.3%** | **2.0%** |
| Return received & QC'd | 17.6% | 32.6% |
| Duplicate/failed payment | 13.2% | 20.5% |
| Warranty buy-back | 4.3% | 16.5% |
| Cancellation | 9.1% | 14.4% |

**Business goal:** cut avoidable refund leakage from **14.6% → 3.7%** of refund
spend — **₹1.22 lakh a quarter, ₹4.87 lakh a year**. Five named buckets, 888
tickets you can open individually. See [`docs/business-impact.md`](docs/business-impact.md).

---

## Assumptions

Full log with evidence in [`docs/decisions.md`](docs/decisions.md) — 17 decisions.
The ones that move numbers:

| ID | Assumption | Basis |
|---|---|---|
| D-03 | Legacy Freshdesk amounts are paise | 125 paired observations, ratio 100.0, zero variance. **Measured, not assumed.** |
| D-02 | The helpdesk row wins a duplicate pair | It is the system of record and already stores rupees, so no conversion is needed |
| D-05 | Finance's ₹1 crore comes from **this** export | Reproducible from it by one unit error. **Unproven** — the one thing to confirm with Arjun. |
| D-08 | Month = `created_at` month | Present on 100% of rows; only 3.4% of refunds fall in a different month on the other basis. `month_resolved` also emitted. |
| D-10 | Refunds on open/pending tickets count | ₹3,17,314 (4.7%). Included and flagged, never silently dropped. |
| D-09 | All timestamps are IST | Tested for a UTC shift; zero negative durations in either system |

---

## Known issues

Honest list. Fuller version in [`docs/validation.md`](docs/validation.md) §"What we know is wrong".

1. **Tier-2 AI accuracy is unmeasured.** Its labels and the gold set came from
   the same model, so measuring one against the other would be circular. Affects
   5.3% of refunds. Fix: Vireo hand-labels 50 tickets, ~1 hour.
2. **The `anthropic` backend has never been executed.** No API key in the build
   environment. Code is written and reviewed; it needs one real run.
3. **707 refund tickets have an ambiguous order join.** Deliberately unresolved
   (D-06). Context only — a test asserts no total depends on the order join.
4. **Replacement detection in free text is high-precision, low-recall.** The true
   conflict count is ≥ 202. Under-counting is the safe direction for a claim.
5. **The ÷100 evidence comes from pairs dated Jan–Sep 2025 only.** Mitigated:
   divisibility-by-100 holds for all 775 legacy amounts.
6. **No root cause for the volume increase.** Tickets more than doubled and that,
   not agent generosity, is what drove refunds up. The data to explain it was not
   supplied. Flagged as the next question.

---

## Repository layout

```
vireo/            pipeline modules (load → validate → normalise → dedupe → joins
                  → agents → policy → canonical → aggregate → ai_classify
                  → reconcile → impact → validate_sample → costs)
tests/            71 tests
app/app.py        Streamlit reviewer
scripts/          one-off Step 1 data-audit scripts (not part of the pipeline; see scripts/README.md)
prompts/          the AI classifier prompt, versioned
data/raw/         supplied files, unmodified
data/derived/     24 generated tables (canonical_refunds.csv is the key one)
data/eval/        168-ticket gold label set
data/ai_labels/   tier-2 label cache (lets a clean machine reproduce the numbers)
reports/          reconciliation.md · validation.md
docs/             requirements · data-audit · decisions · data-dictionary
                  ai-design · validation · business-impact · scope · final-checklist
deliverables/     memo to Arjun Mehta · submission form · recording plan
pyproject.toml    packaging metadata (pip install -e ".[dev]"); Makefile wraps the commands below
```

## Three things a new developer needs to know

1. **`canonical_refunds.csv` is the only table any total may come from.** One row
   per ticket, amounts already in rupees. If you sum anything else, you will
   reproduce Finance's ₹1 crore.
2. **`reason_code` is a fact; `ai_suggested_reason` is an opinion.** Never let
   the second overwrite the first. The pipeline asserts the AI layer cannot
   change a refund total — keep that assert.
3. **The ÷100 is measured, not configured.** `verify_legacy_conversion()`
   re-derives it every run and aborts on disagreement. If a future export breaks
   that, the pipeline stopping is correct behaviour, not a bug to work around.
