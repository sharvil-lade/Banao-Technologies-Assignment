"""
Business impact.

Rules this module follows, because the brief asks for a number and it is easy
to produce a flattering one:

  * Every bucket is a set of named ticket_ids. Nothing is estimated from a rate.
  * A ticket is counted in at most ONE bucket. Buckets are applied in priority
    order and later buckets exclude tickets already claimed.
  * OBSERVED and TARGET are kept apart. The observed figure is what the data
    shows. The target is a judgement with a stated reduction factor and reason.
  * A refund that simply returns money the customer was owed is NOT counted as
    a saving - only the duplicated, capped-breaching or preventable portion is.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config

QUARTERS = 6.0   # the supplied window is 18 months


def _contact_cost(df):
    return (df.channel.map(config.CONTACT_COST_INR).fillna(config.BLENDED_CONTACT_COST_INR).sum()
            + df.transfers_n.fillna(0).sum() * config.TRANSFER_COST_INR)


def build_buckets(refunds: pd.DataFrame) -> pd.DataFrame:
    """Mutually exclusive buckets of avoidable cost, in priority order."""
    claimed: set = set()
    rows = []

    def take(mask, name, amount_fn, kind, reduction, rationale, evidence):
        sub = refunds[mask & ~refunds.ticket_id.isin(claimed)]
        if sub.empty:
            return
        claimed.update(sub.ticket_id)
        total = float(amount_fn(sub))
        rows.append({
            "bucket": name, "tickets": len(sub), "cost_type": kind,
            "observed_total_inr": round(total),
            "observed_per_quarter_inr": round(total / QUARTERS),
            "target_reduction_pct": int(reduction * 100),
            "target_saving_per_quarter_inr": round(total / QUARTERS * reduction),
            "rationale": rationale, "evidence": evidence,
        })

    # 1. Both remedies given. Policy S5 forbids it outright.
    #    Conservative: only the CHEAPER of the two is treated as waste.
    take(refunds.flag_replacement_conflict_any,
         "Duplicate remedy: refund AND replacement on the same order",
         lambda d: np.minimum(d.refund_amount_inr,
                              d.unit_cost_inr + config.REPLACEMENT_LOGISTICS_INR).sum(),
         "money that should not have left", 0.90,
         "Policy S5: 'In no case is a customer to receive both'. The target is zero; "
         "90% allows for genuine exceptions escalated to Finance.",
         "replacement_issued=Y, or the agent's own note states both were given")

    # 2. A discount that should have applied at checkout, paid back later.
    take(refunds.ai_theme == "pricing_coupon",
         "Pricing and coupon refunds: discount not applied at checkout",
         lambda d: d.refund_amount_inr.sum(),
         "preventable at source", 0.70,
         "Each is a checkout defect refunded after the fact. Fixing coupon validation "
         "removes most; 70% leaves room for genuine price-drop goodwill.",
         "ai_theme=pricing_coupon; customer text cites a coupon or advertised price")

    # 3. Genuine goodwill above the policy cap (measured AFTER restatement, so
    #    miscoded refunds are not counted here).
    gw = (refunds.ai_suggested_reason == "GW-OTHER") & (refunds.refund_amount_inr > config.GOODWILL_CAP_INR)
    take(gw, f"Goodwill above the Rs {config.GOODWILL_CAP_INR} cap (after restatement)",
         lambda d: (d.refund_amount_inr - config.GOODWILL_CAP_INR).sum(),
         "money that should not have left", 0.50,
         "Policy S5 caps goodwill and requires Team Lead approval. 50% is deliberately "
         "cautious: some of these may have had approval that the export does not record.",
         "ai_suggested_reason=GW-OTHER and amount > cap; only the excess is counted")

    # 4. Refund released although the goods never came back.
    note = refunds.agent_notes.fillna("").str.lower()
    nopkp = note.str.contains(
        r"(?:rfnd|refund).{0,40}without p(?:ic)?k(?:u)?p|without pickup|"
        r"p(?:k|ick)(?:u)?p not done.{0,80}(?:rfnd|refund)|nobody came for the pickup",
        regex=True)
    take(nopkp, "Refund released without the unit being collected",
         lambda d: d.refund_amount_inr.sum(),
         "money out with no goods back", 0.60,
         "The refund is owed, but releasing it before pickup loses the unit as well. "
         "60% reflects that some releases are a deliberate service call.",
         "agent note states the pickup had not happened when the refund was issued")

    # 5. Handling cost of contacts caused by a broken checkout. The refund itself
    #    is money wrongly collected and returned - deliberately NOT counted.
    take(refunds.ai_theme == "payment_failure",
         "Handling cost of payment-failure contacts",
         _contact_cost, "avoidable handling cost", 0.70,
         "Policy S4 contact costs. The refund is a reversal, not a loss, so only the "
         "cost of the contact is counted. Reliable order creation removes most.",
         "ai_theme=payment_failure; cost = policy S4 channel rate + Rs 305 per transfer")

    out = pd.DataFrame(rows)
    out.attrs["tickets_claimed"] = len(claimed)
    return out


def summarise(refunds: pd.DataFrame, buckets: pd.DataFrame) -> dict:
    baseline_q = refunds.refund_amount_inr.sum() / QUARTERS
    observed_q = buckets.observed_per_quarter_inr.sum()
    target_q = buckets.target_saving_per_quarter_inr.sum()
    return {
        "baseline_refunds_per_quarter_inr": round(baseline_q),
        "avoidable_identified_per_quarter_inr": int(observed_q),
        "avoidable_pct_of_refund_spend": round(observed_q / baseline_q * 100, 1),
        "residual_pct_after_target": round((observed_q - target_q) / baseline_q * 100, 1),
        "target_saving_per_quarter_inr": int(target_q),
        "target_saving_per_year_inr": int(target_q * 4),
        "tickets_involved": int(buckets.tickets.sum()),
    }
