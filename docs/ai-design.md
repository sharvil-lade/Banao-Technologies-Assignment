# The AI layer — design, cost and boundaries

## 1. Where AI is used, and where it is banned

| Question | Answered by | Why |
|---|---|---|
| How much was refunded? | pandas | Deterministic, reproducible, auditable |
| In which month? | pandas | " |
| By which agent, on which team? | pandas | " |
| Under which reason code? | the source system, unchanged | It is a recorded fact |
| **What was the refund actually for?** | **AI, on free text** | Requires reading 2,340 prose notes |
| Is this ticket suspicious? | pandas + policy rules | Policy is written down; no judgement needed |

**The model never sees a number it is asked to add, and never returns one.**
It reads `customer_message` and `agent_notes` and returns a label. Every rupee in
every output is computed by `aggregate.py`. The pipeline asserts this
mechanically:

```python
total_before = refunds.refund_amount_inr.sum()
refunds = ai_classify.attach(refunds, labels)
assert refunds.refund_amount_inr.sum() == total_before, \
    "the AI layer changed a refund total - this must never happen"
```

The recorded `reason_code` is never overwritten (decision D-16). The model's view
lands in `ai_suggested_reason` beside it, with `ai_evidence_quote`,
`ai_confidence`, `ai_model` and `ai_run_id`. Both columns travel together so a
reader can always see which is which, and the UI labels every panel **FACT** or
**INTERPRETATION**.

## 2. Two-tier architecture — and why

The obvious build is "send all 2,340 refunds to a model". We measured that and
rejected it. Instead:

```
        all refunds
             |
   TIER 1 — deterministic rules          free, instant, 100% reproducible
   (ordered regex over agent_notes,
    then customer_message)
             |
     resolved? ---- yes ----> label      2,215 of 2,340  (94.7%)
             |
             no
             |
   TIER 2 — the model                    125 of 2,340  (5.3%)
   (only genuinely ambiguous tickets)
```

Tier 1's pattern list was written by reading a 168-ticket sample by hand. That
sample then became `data/eval/gold_labels.csv`, the set tier 1 is measured
against — so the rules are not marked by their own author's intuition.

**Tier 1 escalates rather than guesses.** There is one failure mode we found by
measuring: when an agent describes a concrete problem *and* uses goodwill
language ("re-pair successful, resolved… refund + replacement given as cx
threatened social media"), keyword order decides the answer and keyword order is
arbitrary. That is a real ambiguity, not a missing pattern, so those tickets go
to tier 2 instead of being resolved wrongly. 46 of the 125 escalations are this
conflict; the other 79 are notes too terse for any rule (`"see prev"`, `"cx ok"`,
`"-"`).

## 3. Measured accuracy

Against the 168-ticket gold set:

| Metric | Value |
|---|---|
| Tier 1 resolved | 159 of 168 (94.6%) |
| Escalated to tier 2 | 9 of 168 (5.4%) |
| **Accuracy on tier-1 resolved labels** | **97.5%** (155 of 159) |
| Remaining tier-1 errors | 4 |

Independent control — agreement with the **recorded** code on the 1,349 refunds
that are *not* GW-OTHER: **90.4%**. This matters. If the classifier simply
reassigned everything it touched, it would disagree with the recorded code
everywhere. It agrees with the agent nine times out of ten where the agent chose
a specific code, and disagrees almost everywhere the agent left the dropdown
default. That asymmetry is the finding.

Full method, failure modes and the honesty caveat about who produced the gold
labels are in `docs/validation.md` (Step 4).

## 4. Cost

Computed by `vireo/costs.py` from the actual data, not estimated by hand.
Prices are published list prices in USD per million tokens; ₹ at 88/USD.

### One full run — all 18 months, 2,340 refunds

| | |
|---|---|
| Tier 1 (free) | 2,215 tickets |
| Tier 2 (model) | 125 tickets, 3 batches |
| Input tokens | 10,301 |
| Output tokens | 5,625 |
| **Cost, Claude Haiku 4.5** | **$0.038 ≈ ₹3.38** |
| Cost, Claude Sonnet 4.5 | $0.115 ≈ ₹10.14 |

### Monthly at Vireo's volume (650 tickets/week)

| | |
|---|---|
| Tickets/month | 2,817 |
| Refund rate (measured, not assumed) | 20.2% |
| Refunds/month | 568 |
| **Model calls/month** | **30** |
| **Cost/month, Haiku** | **₹0.81** |
| Cost/month, Sonnet | ₹2.44 |
| Same job with every refund sent to the model | ₹46.11/month |
| **Saving from the two-tier design** | **94.7%** |

**The honest headline: the API cost is negligible either way.** ₹46/month would
also have been fine. The two-tier design earns its place for three reasons that
matter more than the money:

1. **94.7% of labels are reproducible with no network call.** Anyone can re-run
   the pipeline and get identical output, forever, with no key and no vendor.
2. **Determinism where it is cheap to have.** A regex that matches
   `"cancelled before dispatch"` will match it the same way next year.
3. **The model is pointed at the hard cases only**, which is where measuring its
   accuracy is actually informative.

The real cost of this system is build time, not inference. That number is in the
submission form.

## 5. Backends

| Backend | Needs a key | Use |
|---|---|---|
| `two_tier` *(default)* | no | Rules + the shipped tier-2 label cache. Reproduces every number in this repo on a clean machine. |
| `rules` | no | Tier 1 only. Leaves 5.3% unresolved and says so. The fallback if the cache is lost. |
| `anthropic` | yes | Sends escalated rows to the API. How Vireo would run this monthly. |
| `cache` | no | Read a full pre-computed label file. |

```bash
python -m vireo.pipeline                      # default: two_tier
python -c "from vireo import pipeline; pipeline.run(ai_backend='rules')"
ANTHROPIC_API_KEY=... python -c "from vireo import pipeline; pipeline.run(escalate_backend='anthropic')"
```

## 6. Provenance of the shipped labels — stated plainly

The tier-2 labels in `data/ai_labels/tier2.jsonl` and the gold labels in
`data/eval/gold_labels.csv` were produced by **Claude Opus 5, working through
Claude Code, in this build session** — reading each ticket's text against the
prompt in `prompts/reason_classifier.md`. They were not produced by a scripted
API call, because this build environment had no `ANTHROPIC_API_KEY`.

Two consequences, neither hidden:

- The `anthropic` backend is **complete but unexercised**. It is how Vireo would
  re-run this; it has not been run here.
- The gold set and the tier-2 labels come from the **same model**. That makes the
  gold set sound for measuring **tier 1** (a regex engine, an independent
  system), and **not** sound for measuring tier 2's accuracy against itself. So
  no accuracy figure is claimed for tier 2. The recommendation in
  `docs/validation.md` is that Vireo hand-labels 50 escalated tickets to close
  that gap — about an hour of one person's time.
