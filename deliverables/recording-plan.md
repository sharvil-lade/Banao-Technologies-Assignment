# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **170 seconds of content**, leaving ~10s of slack.

Two screens only - **your terminal and your browser.** Nothing else to
open, nothing else to alt-tab to. Fewer windows means fewer chances to
fumble a switch on camera, and it's easier to hold a phone steady on two
things than five.

This is a **cue card, not a script** - plain, spoken lines to glance at,
not sentences to memorize. Talk naturally off these; don't read them.

---

## Cue card

**0:00–0:20 — The problem** *(terminal)*
> "Finance thought refunds were over a crore a quarter. The helpdesk said
> only about 11 lakh."

*[run: quick sum of the raw file]*
```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/tickets.csv').refund_amount_inr.replace('',None).astype(float).sum())"
```
> "See that? Real number, but you can't just trust the raw file."

**0:20–0:45 — How I used AI** *(same terminal - open `prompts/reason_classifier.md`)*
```bash
cat prompts/reason_classifier.md
```
> "This is the actual prompt I used. It tells the AI: only call something
> goodwill if the person's own words say so - because 'Goodwill / Other'
> is just the first option in the dropdown, so people click it without
> thinking."
> "And AI never touches the money - only the code does the math."

**0:45–1:15 — What changed** *(stay right there, just keep talking - no new window)*
> "First try, I sent all 991 goodwill tickets to the AI, one by one.
> Stopped after 168 - too slow, too expensive. So I flipped it: simple
> rules catch almost everything, AI only looks at the tricky 5%. Cost
> dropped from ₹46 a month to under a rupee. And those 168 I'd already
> done? I used them to test the AI - 97.5% accurate."

**1:15–1:40 — What I threw away** *(terminal - run the test live)*
```bash
python -m pytest tests/test_dedupe.py::test_naive_drop_duplicates_would_have_been_wrong -v
```
> "My first idea for duplicate tickets was just deleting the copies.
> Wrong - 125 of them had different amounts, like ₹900 on one side,
> ₹90,000 on the other. Delete the wrong one, and the number's broken."

**1:40–2:35 — The tool** *(switch to the browser - one tab, click through it live)*
```bash
python -m streamlit run app/app.py
```
- *Monthly:* "March 2026 - 163 refunds, about ₹4.36 lakh."
- *What for / AI:* "This shows what got called goodwill versus what
  people actually said. Booked: ₹29 lakh. Real: ₹1.36 lakh. 43% becomes
  2%."
- *Records → TK-240003:* "Click into any number and see the real ticket.
  Old system said 90,000, new system said 900 - same ticket, off by
  exactly 100 times. True for all 125 like it."

**2:35–2:55 — Proof** *(same tab, one click)*
- *Reconciliation:* "Add it all up - it matches. Nothing missing."

**2:55–3:00 — Close** *(back to terminal)*
> "Clean computer, ten seconds, and you get the real number - ₹11.18 lakh
> a quarter, every rupee checkable."

---

## What's not in the video (on purpose)

- The email thread and the AI-design doc aren't opened on screen - the
  problem and the "what changed" story are told in words instead. Nobody
  needs to watch you scroll a file to believe a sentence.
- The Agents tab isn't shown - the "I didn't rank agents" decision is
  already covered in the memo and the submission form (Q4). The video
  only has three minutes; that point doesn't need its own screen.
- If your player has an address bar / tabs visible, that's fine - "one
  browser tab" means one Streamlit app, not literally zero chrome.

## Preparation checklist

- [ ] `python -m vireo.pipeline` run once already (so the recording isn't waiting on it)
- [ ] `python -m streamlit run app/app.py` already up in a browser tab, on the Monthly tab
- [ ] Terminal font large enough to read on a phone screen
- [ ] Notifications off
- [ ] Rehearse once against a timer - the tool section is the first thing to trim if over

## What to cut if you run long

In this order: the second half of 0:45–1:15 (keep only "cost dropped to
under a rupee"), then the Records-tab duplicate detail, then the close.
**Never cut** the "43% becomes 2%" moment or the reconciliation line -
those are the two findings the whole submission rests on.
