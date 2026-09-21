"""
Cost model for the AI layer.

Written because the assignment asks "what does one run cost, and what would a
month cost at Vireo's volume", and because the answer drove the architecture:
the two-tier design exists to keep this number near zero.

Token counts are estimated at 4 characters per token, which is close enough for
English plus the shorthand in these notes. Prices are USD per million tokens and
are inputs to the model, not measurements - they are stated so they can be
updated rather than buried.
"""
from __future__ import annotations
import pandas as pd
from . import config, ai_classify

CHARS_PER_TOKEN = 4
USD_INR = 88.0  # indicative; stated as an input, not a measurement

# Published list prices, USD per million tokens.
PRICES = {
    "claude-haiku-4-5":  {"in": 1.00, "out": 5.00},
    "claude-sonnet-4-5": {"in": 3.00, "out": 15.00},
}
OUTPUT_TOKENS_PER_TICKET = 45   # one JSON line: id, reason, theme, confidence, evidence
TICKETS_PER_BATCH = 50          # system prompt is re-sent once per batch


def _tok(s):
    return len(str(s)) / CHARS_PER_TOKEN


def measure_run(refunds: pd.DataFrame, labels: pd.DataFrame) -> dict:
    """Token and rupee cost of ONE full pass over this dataset."""
    prompt_tokens = _tok(ai_classify.PROMPT_PATH.read_text(encoding="utf-8"))
    escalated = labels[labels.ai_run_id == "tier2"].ticket_id
    esc = refunds[refunds.ticket_id.isin(escalated)]
    src = ai_classify.build_input(esc)

    ticket_tokens = (src.customer_message.map(_tok) + src.agent_notes.map(_tok) + 12).sum()
    batches = max(1, -(-len(esc) // TICKETS_PER_BATCH))
    in_tokens = ticket_tokens + prompt_tokens * batches
    out_tokens = len(esc) * OUTPUT_TOKENS_PER_TICKET

    out = {
        "refunds_processed": len(refunds),
        "tier1_free": len(refunds) - len(esc),
        "tier2_model_calls": len(esc),
        "escalation_rate_pct": round(len(esc) / max(len(refunds), 1) * 100, 1),
        "batches": batches,
        "input_tokens": int(in_tokens),
        "output_tokens": int(out_tokens),
    }
    for model, p in PRICES.items():
        usd = in_tokens / 1e6 * p["in"] + out_tokens / 1e6 * p["out"]
        out[f"usd_{model}"] = round(usd, 4)
        out[f"inr_{model}"] = round(usd * USD_INR, 2)
    return out


def project_monthly(run: dict, tickets_per_week: int = 650,
                    refund_rate: float | None = None,
                    refunds: pd.DataFrame | None = None,
                    tickets: pd.DataFrame | None = None) -> dict:
    """
    Scale one run to Vireo's stated volume of ~650 tickets a week.

    The refund rate is measured from the data rather than assumed; the
    escalation rate comes from the run just measured.
    """
    if refund_rate is None:
        refund_rate = len(refunds) / len(tickets)
    monthly_tickets = tickets_per_week * 52 / 12
    monthly_refunds = monthly_tickets * refund_rate
    escalated = monthly_refunds * run["escalation_rate_pct"] / 100

    per_ticket_in = run["input_tokens"] / max(run["tier2_model_calls"], 1)
    batches = max(1, -(-int(escalated) // TICKETS_PER_BATCH))
    in_tokens = escalated * per_ticket_in
    out_tokens = escalated * OUTPUT_TOKENS_PER_TICKET

    out = {
        "tickets_per_week": tickets_per_week,
        "monthly_tickets": round(monthly_tickets),
        "measured_refund_rate_pct": round(refund_rate * 100, 1),
        "monthly_refunds": round(monthly_refunds),
        "monthly_model_calls": round(escalated),
        "batches_per_month": batches,
        "monthly_input_tokens": int(in_tokens),
        "monthly_output_tokens": int(out_tokens),
    }
    for model, p in PRICES.items():
        usd = in_tokens / 1e6 * p["in"] + out_tokens / 1e6 * p["out"]
        out[f"monthly_usd_{model}"] = round(usd, 4)
        out[f"monthly_inr_{model}"] = round(usd * USD_INR, 2)

    # What it would cost to skip tier 1 and send every refund to the model.
    naive_in = monthly_refunds * per_ticket_in
    naive_out = monthly_refunds * OUTPUT_TOKENS_PER_TICKET
    p = PRICES["claude-sonnet-4-5"]
    naive_usd = naive_in / 1e6 * p["in"] + naive_out / 1e6 * p["out"]
    out["naive_all_to_model_monthly_inr"] = round(naive_usd * USD_INR, 2)
    out["saving_vs_naive_pct"] = round(
        (1 - out["monthly_inr_claude-sonnet-4-5"] / max(naive_usd * USD_INR, 1e-9)) * 100, 1)
    return out
