"""
Stage 8 - the canonical refund record.

One row per canonical ticket that carries a refund. This is the only table any
downstream number may be built from, and every column in it is either copied
from source, derived by a documented rule, or a flag with written evidence.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import pandas as pd
from . import config

CANONICAL_COLUMNS = [
    # identity & time
    "ticket_id", "month", "month_resolved", "quarter", "created_at", "resolved_at", "status",
    # who
    "agent_id", "agent_name", "agent_team", "agent_tier", "agent_site", "agent_shift",
    "agent_is_tier2", "agent_team_owns_refunds", "roster_match", "assigned_team",
    # how much  (refund_amount_inr is the ONLY field any total may use)
    "refund_amount_inr", "refund_amount_raw", "currency_unit_source", "conversion_factor",
    # what for
    "reason_code", "reason_label", "reason_is_dropdown_default",
    # provenance
    "source_system", "duplicate_status", "duplicate_confidence", "duplicate_evidence",
    "record_role",
    # channel / context
    "channel", "category", "priority", "transfers_n", "csat",
    "replacement_issued", "replacement_flag",
    "order_id", "order_match", "order_candidates", "order_value_inr", "order_qty",
    "order_channel", "order_date", "lot_code",
    "product_sku", "product_name", "product_family", "unit_cost_inr", "retail_price_inr",
    "customer_id", "customer_city", "customer_state", "care_plus",
    # policy flags + evidence
    "flag_refund_and_replacement", "flag_refund_and_replacement_text",
    "flag_replacement_conflict_any", "replacement_conflict_source", "replacement_text_quote",
    "flag_goodwill_over_cap", "goodwill_excess_inr",
    "flag_refund_exceeds_order", "refund_to_order_ratio",
    "flag_unknown_reason_code", "flag_ticket_open", "flag_conflicting_duplicate",
    "flag_legacy_converted", "flag_count", "is_suspicious", "flag_evidence",
    "replacement_cost_inr", "conflict_total_cost_inr",
    # free text, kept so every number can be read back to its source record
    "customer_message", "agent_notes",
    # bookkeeping
    "row_hash", "pipeline_version", "generated_at",
]


def _row_hash(row) -> str:
    key = f"{row.ticket_id}|{row.source_system}|{row.refund_amount_raw}|{row.reason_code}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


def build_canonical_refunds(canonical_tickets: pd.DataFrame) -> pd.DataFrame:
    """Filter to tickets carrying a refund and emit the canonical schema."""
    df = canonical_tickets[canonical_tickets.has_refund].copy()
    df["pipeline_version"] = config.PIPELINE_VERSION
    df["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    df["row_hash"] = [_row_hash(r) for r in df.itertuples()]
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None
    out = df[CANONICAL_COLUMNS].sort_values(["month", "ticket_id"]).reset_index(drop=True)

    # Contract checks. A canonical table that fails these must not be published.
    assert out.ticket_id.is_unique, "canonical refunds contain a repeated ticket_id"
    assert out.refund_amount_inr.notna().all(), "canonical refund with no amount"
    assert (out.refund_amount_inr > 0).all(), "canonical refund not strictly positive"
    assert out.record_role.isin(("single_record", "canonical_of_pair")).all(), \
        "an excluded duplicate reached the canonical table"
    return out


def build_canonical_tickets(canonical_tickets: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicated ticket table - every canonical ticket, refund or not.

    Needed so that refund RATE has an honest denominator. Without it, an agent
    who handles 900 tickets and one who handles 90 look the same in a rupee
    ranking, which is precisely the mistake D-15 exists to prevent.
    """
    cols = ["ticket_id", "month", "quarter", "status", "channel", "category", "priority",
            "assigned_team", "agent_id", "agent_name", "agent_team", "agent_tier",
            "agent_is_tier2", "product_sku", "product_family", "csat", "transfers_n",
            "has_refund", "refund_amount_inr", "reason_code", "source_system",
            "duplicate_status", "record_role"]
    out = canonical_tickets[[c for c in cols if c in canonical_tickets.columns]].copy()
    assert out.ticket_id.is_unique, "canonical ticket table contains a repeated ticket_id"
    return out.sort_values(["month", "ticket_id"]).reset_index(drop=True)
