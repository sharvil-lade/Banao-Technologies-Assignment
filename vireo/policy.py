"""
Stage 7 - policy validation.

Each flag encodes a rule written in support-policy.pdf v3.2, and each one writes
a human-readable sentence into flag_evidence so no reviewer has to reverse-
engineer why a ticket was flagged. Flags never change an amount or a reason code.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
from . import config

# High-precision phrases for "a refund AND a replacement were both given".
# Deliberately conservative: this is reported separately from the structured
# flag, at lower confidence, because it is read out of prose written by agents.
BOTH_PATTERNS = [
    r"refund \+ replacement", r"rfnd \+ rplc", r"refund \+ rplc", r"rfnd \+ replacement",
    r"refund and replacement", r"rfnd and rplc",
    r"both refund and replacement", r"replacement and refund",
    r"issued refund \+ replacement both", r"refund \+ replacement both",
]
BOTH_RE = re.compile("(?:" + "|".join(BOTH_PATTERNS) + ")", re.IGNORECASE)


def _quote(text: str, match: re.Match, width: int = 60) -> str:
    start = max(0, match.start() - width // 2)
    end = min(len(text), match.end() + width // 2)
    return ("..." if start else "") + text[start:end].replace("\n", " ") + ("..." if end < len(text) else "")


def flag_refund_and_replacement(df: pd.DataFrame) -> pd.DataFrame:
    """
    Policy S5: "In no case is a customer to receive both a refund and a
    replacement for the same order; where this happens in error it must be
    escalated to the Team Lead and Finance the same day."

    Two independent detectors, kept separate on purpose:
      - the structured replacement_issued flag (high confidence)
      - the agent's own closing note saying both were given (medium confidence)
    The second exists because the first under-reports: notes reading "issued
    refund + replacement both, TL aware" sit on tickets flagged N.
    """
    out = df.copy()
    out["flag_refund_and_replacement"] = out.has_refund & out.replacement_flag

    notes = out.agent_notes.fillna("")
    matches = notes.map(lambda s: BOTH_RE.search(s))
    out["flag_refund_and_replacement_text"] = out.has_refund & matches.notna()
    out["replacement_text_quote"] = [
        _quote(n, m) if (m is not None) else "" for n, m in zip(notes, matches)
    ]
    # Either signal. This is the number used for business impact.
    out["flag_replacement_conflict_any"] = (
        out.flag_refund_and_replacement | out.flag_refund_and_replacement_text
    )
    out["replacement_conflict_source"] = np.select(
        [out.flag_refund_and_replacement & out.flag_refund_and_replacement_text,
         out.flag_refund_and_replacement,
         out.flag_refund_and_replacement_text],
        ["flag+note", "flag_only", "note_only"], default="",
    )
    return out


def flag_goodwill_cap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Policy S5: "Goodwill credits are capped at Rs 500 per ticket and require
    Team Lead approval."

    A breach here means one of two things and the flag does not decide which:
    either the cap is being exceeded, or the refund is not really goodwill and
    the dropdown default was left in place. That question is what the AI layer
    is for; this flag only states the measurable fact.
    """
    out = df.copy()
    out["flag_goodwill_over_cap"] = (
        out.has_refund
        & (out.reason_code == config.DROPDOWN_DEFAULT_REASON)
        & (out.refund_amount_inr > config.GOODWILL_CAP_INR)
    )
    out["goodwill_excess_inr"] = np.where(
        out.flag_goodwill_over_cap,
        out.refund_amount_inr - config.GOODWILL_CAP_INR, 0.0,
    )
    return out


def flag_amount_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """A refund larger than what the customer paid. Only where the order is known."""
    out = df.copy()
    known = out.order_match.isin(("direct", "fallback_unique")) & out.order_value_inr.notna()
    out["flag_refund_exceeds_order"] = out.has_refund & known & (
        out.refund_amount_inr > out.order_value_inr)
    out["refund_to_order_ratio"] = np.where(
        known & out.has_refund, out.refund_amount_inr / out.order_value_inr, np.nan)
    return out


def flag_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    # Stage contract: policy runs after dedupe. Stated as an assertion so a future
    # reordering fails here with a readable message instead of a bare KeyError.
    assert "duplicate_status" in df.columns, \
        "apply_policy() must run after dedupe.deduplicate() - duplicate_status missing"
    out = df.copy()
    out["flag_unknown_reason_code"] = out.unknown_reason_code
    out["flag_ticket_open"] = out.has_refund & out.ticket_open       # D-10
    out["flag_duplicate_source"] = out.duplicate_status == "exact_migration_pair"
    out["flag_conflicting_duplicate"] = out.duplicate_status == "conflicting_pair"
    out["flag_legacy_converted"] = out.has_refund & out.is_legacy
    return out


def replacement_cost_model(df: pd.DataFrame) -> pd.DataFrame:
    """
    Policy S5: "Replacement cost for planning: the product's unit cost plus
    Rs 340 for reverse pickup and forward shipping. Refurbishment recovery is
    not to be assumed in business cases."

    Applied only to tickets where a replacement conflict was detected, and kept
    in its own column so it never leaks into a refund total.
    """
    out = df.copy()
    out["replacement_cost_inr"] = np.where(
        out.flag_replacement_conflict_any,
        out.unit_cost_inr + config.REPLACEMENT_LOGISTICS_INR, 0.0,
    )
    out["conflict_total_cost_inr"] = np.where(
        out.flag_replacement_conflict_any,
        out.refund_amount_inr.fillna(0) + out.replacement_cost_inr, 0.0,
    )
    return out


FLAG_EXPLANATIONS = {
    "flag_refund_and_replacement":
        "policy S5: refund and replacement both issued (replacement_issued=Y)",
    "flag_refund_and_replacement_text":
        "policy S5: agent note states both a refund and a replacement were given",
    "flag_goodwill_over_cap":
        f"policy S5: GW-OTHER refund above the Rs {config.GOODWILL_CAP_INR} goodwill cap",
    "flag_refund_exceeds_order":
        "refund larger than the order value",
    "flag_unknown_reason_code":
        "reason code not in policy S5 - row kept, not dropped",
    "flag_ticket_open":
        "refund recorded on an open/pending ticket (D-10)",
    "flag_conflicting_duplicate":
        "repeated ticket_id whose rows disagree - both kept, unresolved",
    "flag_legacy_converted":
        "amount converted from legacy paise (D-03, factor 100)",
}
FLAG_COLUMNS = list(FLAG_EXPLANATIONS)


def build_flag_evidence(df: pd.DataFrame) -> pd.DataFrame:
    """One readable sentence per ticket explaining every flag it raised."""
    out = df.copy()
    parts = []
    for _, row in out[FLAG_COLUMNS].iterrows():
        parts.append(" | ".join(FLAG_EXPLANATIONS[c] for c in FLAG_COLUMNS if row[c]))
    out["flag_evidence"] = parts
    out["flag_count"] = out[FLAG_COLUMNS].sum(axis=1).astype(int)
    out["is_suspicious"] = out[[
        "flag_refund_and_replacement", "flag_refund_and_replacement_text",
        "flag_goodwill_over_cap", "flag_refund_exceeds_order",
        "flag_unknown_reason_code", "flag_conflicting_duplicate",
    ]].any(axis=1)
    return out


def apply_policy(df: pd.DataFrame) -> pd.DataFrame:
    out = flag_refund_and_replacement(df)
    out = flag_goodwill_cap(out)
    out = flag_amount_outliers(out)
    out = flag_data_quality(out)
    out = replacement_cost_model(out)
    out = build_flag_evidence(out)
    return out
