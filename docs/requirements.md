# Requirements Matrix — Vireo Audio Support Tickets (Set C)

Source of record: `data/raw/assignment.txt` (verbatim copy of the brief).
Everything below is traced to a line in that file or to the email thread / policy PDF.
Nothing in this table is invented.

## A. Business question (the actual ask)

| # | Stated by | Quote | Interpretation used |
|---|---|---|---|
| Q1 | Arjun Mehta (brief + email 7 Sep) | "monthly refunds by reason code and by agent - who is giving away money and for what" | Monthly refund totals, split by `refund_reason_code` and by `agent_id`. "What for" = the reason behind the refund, not only the dropdown code. |
| Q2 | Arjun Mehta (email 9 Sep) | "Rs 11 lakh a quarter versus my crore - one of us is reading the export wrong… I want the total to reconcile." | A reconciliation is a **first-class deliverable**, not a footnote. The tool must explain the gap between the two numbers. |
| Q3 | Arjun Mehta (brief) | "Something I can drop straight into the board pack." | Output must be presentable and monthly. Board pack date: 24 Sep. |
| Q4 | Priya Raman (email 8 Sep) | "refunds went up because we told the frontline to stop arguing… CSAT went up 0.4" | A stated causal claim from the client. Must be tested against data, not repeated or ignored. |
| Q5 | Neha Kulkarni (email 8 Sep) | "in a couple the customer also got a new unit sent out. Probably one-offs" | A specific hypothesis to quantify. Policy §5 forbids refund + replacement. |
| Q6 | Sameer Qureshi (email 7 Sep) | "the first option in the list is GW-OTHER… and agents are agents" | Explicit warning of a default-selection bias in reason codes. Must be tested. |

## B. Required inputs

| Input | Provided | Location in repo | Used for |
|---|---|---|---|
| `tickets.csv` | yes | `data/raw/tickets.csv` | Primary fact table |
| `agents.csv` | yes | `data/raw/agents.csv` | Agent name / team / tier / site resolution |
| `orders.csv` | yes | `data/raw/orders.csv` | Order value context, outlier checks |
| `customers.csv` | yes | `data/raw/customers.csv` | Customer context, care_plus |
| `products.csv` | yes | `data/raw/products.csv` | Unit cost for replacement-cost model; retail price for outlier checks |
| `support-policy.pdf` | yes | `data/raw/support-policy.pdf` | Refund rules, reason-code list, cost standards, systems/timestamps |
| `email-thread.txt` | yes | `data/raw/email-thread.txt` | Client context, competing numbers, hypotheses |
| `README.txt` (data pack) | yes | `data/raw/README-datapack.txt` | Column definitions |

No external data is used. No figures are taken from outside this pack.

## C. Required outputs / deliverables

| # | Deliverable (brief wording) | Planned implementation | Step |
|---|---|---|---|
| D1 | "A working AI-assisted tool… must start from your README on a clean machine" | Python package `vireo/` + CLI + a single-file local Streamlit UI. `pip install -r requirements.txt` then two commands. | 2–3 |
| D2 | "A business goal, stated as a number" | Derived from the dataset in Step 4. Candidate identified in audit (see `data-audit.md` §7), **not yet committed**. | 4 |
| D3 | "Some way of showing it works" | Reconciliation bridge + deterministic unit tests + manually-labelled validation sample + measured AI accuracy. | 2 & 4 |
| D4 | "A one-page memo to Arjun Mehta… eleven minutes of reading, maximum" | `deliverables/memo-arjun-mehta.md` | 5 |
| D5 | "A screen recording… at most three minutes" | `docs/recording-plan.md` (script + shot list). Recording itself is the candidate's to capture. | 5 |
| D6 | "Complete `submission-form.md` from this pack" | `deliverables/submission-form.md`, every field answered. | 5 |

Note on D6: a file literally named `submission-form.md` is **not present** in the pack.
The questions that would be on it are listed at the bottom of `assignment.txt`.
Decision: reconstruct the form from those questions verbatim. Logged in `decisions.md` (D-01).

## D. Runtime and scope expectations

| Constraint | Source | Consequence for build |
|---|---|---|
| 48-hour window, ~5 hours effort, "we mean the cap" | assignment.txt | Small, single-machine, no infrastructure. No database, no cloud, no auth. |
| "A small thing that runs beats a large thing that does not" | assignment.txt | Streamlit over a React app. CSV over a warehouse. |
| "There is more here than fits in five hours… what you choose to leave out… matters as much" | assignment.txt | An explicit scope-decision section is a scored deliverable, written in Step 4. |
| Volume ≈ 650 tickets/week | assignment.txt Q2 | Cost model must be expressed per run and per month at this volume. |

## E. AI requirements

| Requirement | Source | Plan |
|---|---|---|
| "Any stack, any models" | assignment.txt | Free choice. |
| "What you used / what it cost / what you discarded" | assignment.txt | Tracked from the first line of code; reported in the submission form. |
| No penalty or bonus for AI use | assignment.txt | AI used only where it beats a deterministic rule: free-text interpretation. |
| (self-imposed) No LLM arithmetic | user brief, principle 9 | All money is computed in pandas. The LLM never sees a number it is asked to add. |

## F. Validation requirements

| Requirement | Source | Plan |
|---|---|---|
| "How do you know it works?" — sample size, method, error rate, failure mode | assignment.txt Q3 | Step 4: 3 layers — (a) deterministic reconciliation identities, (b) hand-checked record sample, (c) labelled AI eval set. |
| "I want the total to reconcile" | email 9 Sep | Reconciliation bridge from the raw export sum to the canonical total, every step signed and reversible. |

## G. Documentation requirements

| Requirement | Source | Artefact |
|---|---|---|
| README must work on a clean machine | assignment.txt | `README.md` (Step 5) |
| Decisions written down and explained | assignment.txt, "On the brief itself" | `docs/decisions.md` (live from Step 1) |
| Three things a Monday-morning stranger needs | assignment.txt Q10 | Submission form + README |

## H. Explicitly left open by the brief

| Open point | Our handling |
|---|---|
| Shape of the "showing it works" deliverable | Chosen: reconciliation + tests + sampled validation + AI eval. Logged D-13. |
| Stack and models | Chosen: Python/pandas + Streamlit; Claude for free-text only. Logged D-14. |
| What the business goal should be | Deliberately deferred to Step 4, after the data is trustworthy. |
| Whether "refunds" includes SLA store credits | Investigated; see `data-audit.md` §6.9 and decision D-11. |
| Month basis (created vs resolved) | Investigated; decision D-08. |

## I. Requirement → implementation map

| Requirement | Module / artefact | Verified by |
|---|---|---|
| Monthly refund totals | `vireo/aggregate.py` | `tests/test_aggregate.py`, reconciliation identity |
| By reason code | `vireo/aggregate.py` | identity: Σ reason = canonical total |
| By agent | `vireo/agents.py` + `aggregate.py` | identity: Σ agent = canonical total |
| Reconcile ₹1 cr vs ₹11 L | `vireo/reconcile.py` → `reports/reconciliation.md` | bridge sums to zero residual |
| Duplicate handling | `vireo/dedupe.py` | `tests/test_dedupe.py`; audit trail CSV |
| Legacy money unit | `vireo/normalise.py` | 125 paired observations, ratio = 100.0 exactly |
| "What for" | `vireo/ai_classify.py` | labelled eval set, Step 4 |
| Suspicious cases | `vireo/policy.py` | `tests/test_policy.py`, evidence column per flag |
| Reviewer interface | `app/app.py` (Streamlit) | manual walkthrough, Step 3 |
| Memo | `deliverables/memo-arjun-mehta.md` | Step 5 |
