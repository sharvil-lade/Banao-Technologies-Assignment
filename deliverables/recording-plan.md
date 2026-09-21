# Screen recording plan — 3 minutes maximum

The brief asks the recording to show: **the prompts used · what changed
between versions · what was thrown away**, plus the working tool. **No
slides.** Phone recording of the screen is fine.

Budget: **175 seconds of content**, leaving ~5s of slack.

This is a **cue card, not a script** — plain, spoken lines to glance at, not
sentences to memorize. Say them in your own words if that feels more
natural; the point is what to show and roughly what to say, not word-for-word
delivery.

---

## Cue card

**0:00–0:20 — The problem**
*[email-thread.txt, Arjun's message]*
> "Finance thought refunds were over a crore a quarter. The helpdesk said
> only about 11 lakh. So — who's right?"

*[run the raw sum in terminal]*
```bash
python -c "import pandas as pd; print(pd.read_csv('data/raw/tickets.csv').refund_amount_inr.replace('',None).astype(float).sum())"
```
> "If you just add up the raw file... yeah, you get 23 crore. So the number's
> real, but you can't just add up the file and trust it."

**0:20–0:50 — How I used AI**
*[prompts/reason_classifier.md]*
> "I used AI, but only to read text — never to touch the money."
> "Like here — I only mark something as goodwill if the words actually say
> so. Because 'Goodwill / Other' is just the first option in the dropdown,
> so people click it without thinking."
> "My rule: if the computer can calculate it, let it calculate it. Don't ask
> AI to do the math."

**0:50–1:20 — What changed**
*[docs/ai-design.md, the diagram]*
> "At first I planned to send all 991 goodwill tickets to the AI, one by
> one. I did 168 and stopped — too slow, too expensive, and I couldn't even
> check if it was right."
> "So I flipped it: simple rules catch almost everything first, AI only
> looks at the tricky 5%."
> "Cost dropped from about ₹46 a month to under a rupee."
> "And those 168 I'd already done? I used them to test how accurate the AI
> actually is — 97.5%."

**1:20–1:45 — What I threw away**
*[run, live]*
```bash
python -m pytest tests/test_dedupe.py::test_naive_drop_duplicates_would_have_been_wrong -v
```
> "My first idea for the duplicate tickets was just to delete the copies.
> Turns out that was wrong — 125 of them had different amounts on each side,
> like ₹900 versus ₹90,000. Delete the wrong one, and the whole number's
> wrong."
> "I also tried costing out repeat complaints as a savings idea, but
> couldn't prove it cleanly, so I dropped it."

**1:45–2:35 — The tool**
```bash
python -m streamlit run app/app.py
```
*[Monthly, pick 2026-03]*
> "March 2026 — 163 refunds, about ₹4.36 lakh."

*[What for / AI]*
> "This shows what got booked as goodwill versus what people actually said.
> Booked: ₹29 lakh. Real goodwill: ₹1.36 lakh. So 43% turns into 2%."

*[Agents]*
> "I show agents here too, but I didn't rank them — three teams just handle
> way more refunds as part of their job. Ranking them would be unfair."

*[Records → TK-240003]*
> "Any number here, you can click into and see exactly which ticket it came
> from — the plain facts on one side, the AI's read on the other."

**2:35–2:55 — Proof**
*[Duplicate audit, TK-240003]*
> "This one ticket: old system says 90,000, new system says 900. Exactly
> 100 times off — true for all 125 pairs, no exceptions."

*[Reconciliation tab]*
> "Add it all up and it matches, perfectly. Nothing left over."

**2:55–3:00 — Close**
*[terminal, pipeline finishing]*
> "From a totally clean computer, about 10 seconds, and you get the real
> number: ₹11.18 lakh a quarter — and you can check every rupee."

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
