# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **175 seconds of content**, leaving ~5s of slack.

This is a **cue card, not a script** — short phrases to glance at and speak
naturally off, not sentences to read verbatim. Reading full sentences on
camera sounds stiff and eats the time budget; talking naturally off short
cues doesn't.

---

## Cue card

**0:00–0:20 — The problem**
*[email-thread.txt, Arjun's message]*
- Finance: >1 crore/qtr. Helpdesk: ~11 lakh. Which one's right?

*[run: raw CSV sum in terminal]*
```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/tickets.csv').refund_amount_inr.replace('',None).astype(float).sum())"
```
- "Raw export sums to ~23 crore — reproducible, but unusable as-is."

**0:20–0:50 — Using AI carefully**
*[prompts/reason_classifier.md]*
- "AI only classifies text — never touches the money."
- "Rule: only call it goodwill if the text actually says so — GW-OTHER is
  the dropdown default, easy to over-trust."
- "If pandas can compute it, pandas computes it."

**0:50–1:20 — What changed**
*[docs/ai-design.md, the two-tier diagram]*
- "First plan: send all 991 goodwill tickets to the model. Stopped after
  168 — wrong architecture."
- "Switched to two-tier: rules first, model only for the ~5%."
- "Cost dropped ₹46 → ₹0.81 a month."
- "Those 168 became my evaluation set instead — 97.5% measured accuracy."

**1:20–1:45 — What I threw away**
*[run, live]*
```bash
python -m pytest tests/test_dedupe.py::test_naive_drop_duplicates_would_have_been_wrong -v
```
- "First dedupe: `drop_duplicates()`. Wrong — 125 of 638 pairs have
  different amounts, ₹900 vs ₹90,000. Would've silently corrupted the
  number."
- "Also dropped repeat-contact costing — couldn't defend the assumption."

**1:45–2:35 — The tool**
```bash
python -m streamlit run app/app.py
```
- *[Monthly, pick 2026-03]* — "163 refunds, ₹4.36L."
- *[What for / AI]* — "Booked as goodwill: ₹29L. Text actually supports:
  ₹1.36L. 43% becomes 2%."
- *[Agents]* — "Not a leaderboard on purpose — Returns, Billing, Logistics
  do most refunds by design."
- *[Records → TK-240003]* — "Every number traces to one ticket — fact on
  the left, AI read on the right."

**2:35–2:55 — Proof**
- *[Duplicate audit, TK-240003]* — "Helpdesk 900, legacy 90,000. Ratio
  exactly 100 — across all 125 pairs, zero variance."
- *[Reconciliation tab]* — "Residual: ₹0.00."

**2:55–3:00 — Close**
*[terminal, pipeline finishing]*
- "Clean machine, ~10 seconds. ₹11.18 lakh a quarter — fully traceable."

---

## Preparation checklist

- [ ] `python -m vireo.pipeline` run once already (so the recording isn't waiting on it)
- [ ] `python -m streamlit run app/app.py` already up in a browser tab, on the Monthly tab
- [ ] Terminal font large enough to read on a phone screen
- [ ] Tabs pre-opened: `email-thread.txt`, `prompts/reason_classifier.md`, `docs/ai-design.md`
- [ ] Notifications off
- [ ] Rehearse once against a timer — the tool section is the first thing to trim if over

## What to cut if you run long

In this order: the second half of 1:20–1:45 (keep only the `drop_duplicates`
test), then the Agents tab, then the close. **Never cut** the 2:35–2:55
validation example or the "43% becomes 2%" moment — those are the two
findings the whole submission rests on.
