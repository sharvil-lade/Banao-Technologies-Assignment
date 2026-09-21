# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed between
versions · what was thrown away**, plus the working tool. **No slides.** Phone
recording of the screen is fine.

Budget: **175 seconds of content**, leaving ~5s of slack. Nothing is scripted
word-for-word — these are the beats and what must be visible on screen.

---

## Shot list

### 0:00–0:20 · The problem, in the client's own words (20s)
**On screen:** `data/raw/email-thread.txt` open, scrolled to Arjun's 9 Sep message.
**Say:** "Finance says over a crore a quarter. The helpdesk says eleven lakh.
Same file. One of them is reading it wrong."
**Then:** run in a terminal —
```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/tickets.csv').refund_amount_inr.replace('',None).astype(float).sum())"
```
→ `230124081.0` appears. "There's the crore. It's reproducible."

### 0:20–0:50 · The prompts (30s)
**On screen:** split — `prompts/reason_classifier.md` on one side, the Claude Code
session on the other.
**Show two things:**
1. The classifier prompt, specifically the line *"Only return GW-OTHER when the
   text positively indicates a discretionary goodwill gesture"* — and say why
   that line exists (GW-OTHER is the dropdown default).
2. The build prompt's standing rule: *"Do not use an LLM for arithmetic that can
   be done deterministically."*
**Say:** "Every rupee is pandas. The model only ever returns a label."

### 0:50–1:20 · What changed between versions (30s)
**On screen:** `docs/ai-design.md` §2, the two-tier diagram.
**Say:** "Version one sent all 991 goodwill tickets to a model. I got 168 through
and stopped — wrong architecture. Version two puts deterministic rules first."
**Show the numbers on screen:** 94.7% resolved free, 5.3% escalated,
₹46/month → ₹0.81/month.
**The punchline:** "And the 168 tickets weren't wasted — they became the
evaluation set. So instead of an assumed accuracy I have a measured one: 97.5%."

### 1:20–1:45 · What was thrown away (25s)
**On screen:** run the test, live —
```bash
python -m pytest tests/test_dedupe.py::test_naive_drop_duplicates_would_have_been_wrong -v
```
**Say:** "The first dedupe used `drop_duplicates`. 125 of the 638 pairs differ on
amount, so it would have banked a paise value as rupees — ninety thousand rupees
where the truth is nine hundred. This test exists to prove the bug I removed."
**Also name, quickly:** repeat-contact costing (built, measured at ₹1.23 L/qtr,
dropped as undefendable) and the roster fast path a test caught.

### 1:45–2:35 · The tool (50s)
**On screen:** `streamlit run app/app.py`
- **Monthly** — pick `2026-03`, ₹4,35,773 across 163 refunds.
- **What for (AI)** — the two metrics side by side: booked as goodwill
  ₹29,07,036, text supports ₹1,35,652. "43% becomes 2%."
- **Agents** — pause on the policy §6 warning banner. Say: "I was asked who's
  giving away money. The top three are Returns Desk, Billing and Logistics —
  the teams whose job is refunds. I'm not handing Finance a league table."
- **Records** — open `TK-240003`. FACT panel left, INTERPRETATION panel right.

### 2:35–2:55 · The validation example (20s)
**On screen:** stay on `TK-240003`, scroll to the duplicate-audit row.
**Say:** "Helpdesk says 900. Legacy says 90000. Ratio exactly 100 — and that
holds for all 125 pairs where both systems recorded an amount, with zero
variance. That's not an assumption about paise, it's a measurement. After
conversion all 125 pairs agree to the rupee."
**Then:** Reconciliation tab → the bridge → **Residual ₹0.00**.

### 2:55–3:00 · Close (5s)
**On screen:** terminal, `python -m vireo.pipeline` finishing.
**Say:** "Ten seconds, clean machine, no API key. ₹11.18 lakh a quarter, and it
reconciles."

---

## Preparation checklist

- [ ] `python -m vireo.pipeline` run once already (so the recording isn't waiting on it)
- [ ] `streamlit run app/app.py` already up in a browser tab, on the Monthly tab
- [ ] Terminal font large enough to read on a phone screen
- [ ] Tabs pre-opened: `email-thread.txt`, `prompts/reason_classifier.md`, `docs/ai-design.md`
- [ ] Notifications off
- [ ] Rehearse once against a timer — the tool section is the first thing to trim if over

## What to cut if you run long

In this order: the second half of 1:20–1:45 (keep only the `drop_duplicates`
test), then the Agents tab, then the close. **Never cut** the 2:35–2:55
validation example or the "43% becomes 2%" moment — those are the two findings
the whole submission rests on.
