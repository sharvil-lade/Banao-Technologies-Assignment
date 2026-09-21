# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **170 seconds of content**, leaving ~10s of slack.

Two screens, two actions: **run the pipeline once, then walk the app.**
Nothing else to open. The problem, the AI usage, what changed, and what
got thrown away are all spoken while the pipeline runs or its output sits
on screen - not shown as separate files.

**One trade-off, on purpose:** the brief asks the video to "walk through
the prompts you used." Not opening `prompts/reason_classifier.md` on
screen means that beat is spoken, not shown - the cue card below quotes
the actual rule word-for-word so it's still genuinely covered, just not
visually. If you'd rather be safe, glancing at that file for 3 seconds
during the 0:15-0:45 beat is cheap insurance; it isn't required by this
plan.

This is a **cue card, not a script** - plain, spoken lines to glance at,
not sentences to memorize. Talk naturally off these; don't read them.

---

## Cue card

**0:00–0:15 — Start it** *(terminal)*
```bash
python -m vireo.pipeline
```
> "Finance thought refunds were over a crore a quarter. Helpdesk said only
> about 11 lakh. This sorts out which one's real."

**0:15–0:45 — AI + what changed** *(same terminal, output scrolling)*
> "I used AI only to read the ticket text - never for the money, only the
> code does math. The rule: only call something goodwill if the person's
> own words actually say so, because 'Goodwill / Other' is just the first
> option in the dropdown."
> "First try, I sent all 991 goodwill tickets to the AI, one by one -
> stopped after 168, too slow, too expensive. So I flipped it: simple
> rules catch almost everything, AI only looks at the tricky 5%. Cost
> dropped from ₹46 a month to under a rupee, and I reused those 168 to
> test the AI - 97.5% accurate."

**0:45–1:10 — What I threw away** *(point at the terminal output)*
> "My first idea for duplicate tickets was just deleting the copies.
> Wrong - 125 of them had different amounts, ₹900 on one side, ₹90,000 on
> the other. Delete the wrong one, the number's broken. Also tried costing
> out repeat complaints as a savings idea - couldn't prove it, dropped
> it."

*[point at "residual=Rs 0.00 identities=ALL PASS" in the output]*
> "And it all reconciles - nothing left over."

**1:10–2:40 — The app** *(browser, one tab)*
```bash
python -m streamlit run app/app.py
```
- *Monthly:* "March 2026 - 163 refunds, about ₹4.36 lakh."
- *What for / AI:* "Booked as goodwill: ₹29 lakh. Real: ₹1.36 lakh. 43%
  becomes 2%."
- *Records → TK-240003:* "Click any number, see the real ticket - old
  system said 90,000, new system said 900, same ticket, off by exactly
  100. True for all 125 like it."
- *Reconciliation:* "Add it all up - matches, nothing missing."

**2:40–3:00 — Close** *(back to terminal)*
> "Clean computer, ten seconds, and you get the real number - ₹11.18 lakh
> a quarter, every rupee checkable."

---

## What's not in the video (on purpose)

- No separate prompt file, no live pytest run, no email thread, no
  AI-design doc - all spoken instead of shown (see the trade-off note
  above).
- The Agents tab isn't shown - "I didn't rank agents" is already covered
  in the memo and the submission form (Q4).

## Preparation checklist

- [ ] `python -m vireo.pipeline` run once already (so you know the output
      and timing, even though you'll run it again on camera)
- [ ] `python -m streamlit run app/app.py` already up in a browser tab, on
      the Monthly tab, so switching to it is instant
- [ ] Terminal font large enough to read on a phone screen
- [ ] Notifications off
- [ ] Rehearse once against a timer - the app section is the first thing
      to trim if over

## What to cut if you run long

In this order: the second half of 0:15–0:45 (keep only "cost dropped to
under a rupee"), then the Records-tab duplicate detail, then the close.
**Never cut** the "43% becomes 2%" moment or the reconciliation line -
those are the two findings the whole submission rests on.
