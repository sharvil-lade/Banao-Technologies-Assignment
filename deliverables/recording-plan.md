# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **~170 seconds of content**, leaving ~10s of slack.

This is a **script to speak naturally off, not memorize word-for-word.**
Screens: email thread → VS Code (`vireo/pipeline.py`) → terminal →
`docs/ai-design.md` → browser (the app) → terminal for the close.

---

## Script

**0:00–0:20 — Problem Statement** *(email thread)*
> "The main problem was that Vireo's refund numbers were not matching.
> Finance was seeing over ₹1 crore per quarter, while the helpdesk showed
> around ₹11 lakh. So I needed to find out where this difference was
> coming from and build a reliable way to analyze the refunds."

**0:20–0:40 — Solution** *(VS Code)*
> "My solution was to build a small pipeline that cleans the data, finds
> duplicate records, fixes the different money formats, and creates one
> clean refund dataset. I then built a simple app on top of this data to
> analyze the refunds."

**0:40–1:15 — Pipeline** *(`vireo/pipeline.py`)*
> "This is the main pipeline. It checks the data, finds duplicate
> records, connects the tickets with the other files, and fixes the old
> money format to build the final refund dataset. I also use AI only
> when the text needs to be understood - the rest of the calculations
> are done with fixed rules, so the numbers stay consistent. And the
> rule I gave the AI: only call something goodwill if the text itself
> says so, not just because it's the first option in the dropdown."

*[Run]*
```bash
python -m vireo.pipeline
```

*[briefly show `docs/ai-design.md`]*
> "Initially, I was sending all the cases to AI. I changed this to use
> rules first and AI only for the unclear cases. I also removed a simple
> duplicate approach because it was changing some refund amounts."

**1:15–2:20 — App**
```bash
python -m streamlit run app/app.py
```
> "This is the final app - it has seven views: monthly summary, reason
> codes, agents, AI interpretation, suspicious cases, records, and
> reconciliation. Let me walk through the key ones."

*Monthly*
> "The Monthly page shows the refund amount month by month. For March
> 2026, there were 163 refunds totaling around ₹4.36 lakh."

*What For*
> "This page looks at what the customer and agent actually wrote, and
> helps check whether the refund reason matches the text."

*Agents*
> "The Agents page shows the refund numbers for each agent, without
> treating it as a simple ranking."

*Records* *(open `TK-240003`)*
> "And the Records page lets us go back to the original ticket and see
> where the number came from."

**2:20–2:45 — Validation** *(`TK-240003` + reconciliation)*
> "This ticket had ₹900 in the current system and ₹90,000 in the old
> system. I found the same 100-to-1 difference across all 125 matching
> records. After fixing this, the final reconciliation has zero
> difference."

*[Show]*
```text
Residual: ₹0.00
```

**2:45–2:55 — Closing** *(terminal)*
> "So the final result is a clean, repeatable pipeline, a simple refund
> analysis app, and a reconciled figure of around ₹11.18 lakh per
> quarter."

---

## Edits made to the draft, and why

1. **Added the AI-rule line** in the Pipeline beat ("only call something
   goodwill if the text itself says so..."). The brief requires the
   video to cover "the prompts you used" - three drafts in a row left
   this out entirely; this closes it in one sentence, no new screen.
2. **Added a one-line app intro** naming all seven real tabs (checked
   against `app/app.py`: Monthly, Reason codes, Agents, What for (AI),
   Suspicious cases, Records, Reconciliation) before diving into the
   four you actually demo - so the viewer knows the app's full scope,
   not just the slice shown.
3. **Trimmed for timing.** The draft summed to exactly 3:00 with zero
   buffer - one stumble and you're over the hard cap. Shaved a few
   seconds off the Pipeline and App beats to leave ~10s of slack.

All numbers checked against the live data - no factual corrections
needed this round.

## Preparation checklist

- [ ] `vireo/pipeline.py` open in VS Code, scrolled to a readable point
      before you start recording
- [ ] `python -m vireo.pipeline` run once already, so you know the timing
- [ ] `python -m streamlit run app/app.py` already up in a browser tab, on
      the Monthly tab, so switching to it is instant
- [ ] Terminal font large enough to read on a phone screen
- [ ] Notifications off
- [ ] Rehearse once against a timer - the App section is the first thing
      to trim if over

## What to cut if you run long

In this order: the Agents-tab line, then the "seven views" intro
sentence (just open the app and go straight to Monthly), then the AI-rule
sentence in the Pipeline beat. **Never cut** the What For numbers or the
reconciliation line - those are the two findings the whole submission
rests on.
