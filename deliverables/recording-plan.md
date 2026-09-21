# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **~175 seconds of content**, leaving a few seconds of slack.

This is a **script to speak naturally off, not memorize word-for-word.**
Screens: VS Code (`vireo/pipeline.py`) → terminal → browser (the app) →
terminal again for the close.

---

## Script

**0:00–0:30 — Main Pipeline** *(VS Code → `vireo/pipeline.py`)*
> "Let me quickly walk through what I built. The pipeline starts with the
> raw support data and does the main reconciliation work - validation,
> duplicate detection, normalization, and joins. It then creates a
> canonical refund dataset, which is what all the final numbers are
> calculated from. I kept the financial calculations deterministic, and
> AI is only used where we need to interpret the support text."

*[Run]*
```bash
python -m vireo.pipeline
```
> "Once the pipeline finishes, I have the reconciled data that powers the
> application."

**0:30–0:55 — What changed / AI** *(pipeline or `docs/ai-design.md`)*
> "My first approach sent all goodwill cases to the model. I changed that
> to deterministic rules first, and AI only for the cases that actually
> need interpretation. The rule I gave it: only call something goodwill
> if the text itself says so - not just because it's the first option in
> the dropdown. I also removed the simple duplicate approach because it
> wasn't safe for the legacy data. So the final pipeline is smaller,
> cheaper, and easier to validate."
> "Those changes brought AI usage down to about 5 percent, and when I
> checked the rule-based labels against a sample I hand-checked, they
> matched 97.5 percent of the time."

**0:55–2:25 — App Demo**
```bash
streamlit run app/app.py
```

*Monthly*
> "First, the Monthly view gives the overall refund picture."

*[Select `2026-03`]*
> "For March, there are 163 refunds totaling around ₹4.36 lakh."

*What For*

*[Open What For / AI]*
> "This is where AI adds value. It looks at the customer message and
> agent notes and checks what the text actually supports, instead of
> blindly trusting the refund label."

*[Show the two numbers]*
> "Here we can see the difference between what was booked as goodwill
> and what the text actually supports."

*Agents*

*[Open Agents]*
> "The agent view lets Finance investigate who is associated with the
> refunds. But I deliberately didn't make this a simple leaderboard,
> because different teams have different responsibilities."

*Records*

*[Open `TK-240003`]*
> "And finally, every result is traceable back to the original ticket.
> The source facts and the AI interpretation are shown separately."

**2:25–2:50 — Validation** *(duplicate audit / reconciliation)*
> "This is one example of the validation. The current system has ₹900
> and the legacy record has ₹90,000. The same 100-to-1 relationship held
> across all 125 pairs, no exceptions. After normalization, the
> reconciliation has zero residual."

**2:50–3:00 — Close** *(pipeline output / final result)*
> "So the final result is a reproducible pipeline, a traceable refund
> analysis, and a reconciled figure of around ₹11.18 lakh per quarter."

---

## Two edits made to the original draft, and why

1. **Added one line naming the actual prompt rule** (in the 0:30–0:55
   beat): the brief specifically asks the recording to walk through "the
   prompts you used." The original draft never named or quoted one - this
   closes that gap in one sentence, no new screen needed.
2. **Reworded the 97.5% accuracy line.** Sitting right next to "AI usage
   down to 5 percent," the original phrasing could sound like it's the
   *model's* accuracy on the escalated 5% of cases - but tier-2 accuracy
   is explicitly unmeasured (see `docs/validation.md` / the submission
   form's "what's wrong with this" answer). 97.5% is actually the
   deterministic rules' accuracy against the hand-checked sample. Reworded
   so the video doesn't accidentally contradict what the docs already say
   honestly. Also changed "the duplicate pairs I checked" to "all 125
   pairs, no exceptions" - it wasn't a sample, it was all of them, and
   that's the stronger, more accurate claim.

## Preparation checklist

- [ ] `vireo/pipeline.py` open in VS Code, scrolled to a readable point
      (e.g. the `run()` function) before you start recording
- [ ] `python -m vireo.pipeline` run once already, so you know the timing
- [ ] `python -m streamlit run app/app.py` already up in a browser tab, on
      the Monthly tab, so switching to it is instant
- [ ] Terminal font large enough to read on a phone screen
- [ ] Notifications off
- [ ] Rehearse once against a timer - the App Demo section is the first
      thing to trim if over

## What to cut if you run long

In this order: the Agents-tab detour, then the second sentence of
0:30–0:55, then the close. **Never cut** the "What For" numbers or the
reconciliation line - those are the two findings the whole submission
rests on.
