"""
Stage 4 - duplicate / migration detection.

We never call drop_duplicates() on the raw frame. Duplicate pairs are NOT
identical: 125 of the 638 differ on refund_amount_inr because the two systems
store money in different units. A naive drop would keep whichever row happened
to come first and silently bank a paise value as rupees.

Instead: detect, evidence, choose, and keep the loser in an audit table.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config


def detect_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify every row's duplicate status and record why.

    Confidence is earned, not assumed:
      exact_migration_pair - ticket_id repeated, one helpdesk + one legacy_fd row,
                             and all 18 business columns agree. High confidence.
      conflicting_pair     - ticket_id repeated but business columns disagree.
                             Low confidence: the pipeline keeps BOTH and flags them
                             rather than guessing which is right.
      unique               - ticket_id appears once.
    """
    out = df.copy()
    out["_n"] = out.groupby("ticket_id")["ticket_id"].transform("size")

    dup = out[out._n > 1]
    status = pd.Series("unique", index=out.index, dtype=object)
    evidence = pd.Series("ticket_id appears once", index=out.index, dtype=object)
    confidence = pd.Series("n/a", index=out.index, dtype=object)

    if len(dup):
        cols = [c for c in config.DUPLICATE_MATCH_COLUMNS if c in dup.columns]
        agree = dup.groupby("ticket_id")[cols].nunique().max(axis=1) == 1
        srcs = dup.groupby("ticket_id").source_system.apply(lambda s: set(s))
        cross_system = srcs.apply(lambda s: s == {"helpdesk", "legacy_fd"})
        size2 = dup.groupby("ticket_id").size() == 2

        exact = agree & cross_system & size2
        ids_exact = set(exact[exact].index)
        ids_conflict = set(exact[~exact].index)

        m_exact = out.ticket_id.isin(ids_exact) & (out._n > 1)
        m_conf = out.ticket_id.isin(ids_conflict) & (out._n > 1)
        status[m_exact] = "exact_migration_pair"
        confidence[m_exact] = "high"
        evidence[m_exact] = (
            f"{len(cols)}/{len(cols)} business columns identical across "
            "helpdesk+legacy_fd pair; money unit differs by design (policy S9)"
        )
        status[m_conf] = "conflicting_pair"
        confidence[m_conf] = "low"
        evidence[m_conf] = "ticket_id repeated but business columns disagree - BOTH rows kept"

    out["duplicate_status"] = status
    out["duplicate_confidence"] = confidence
    out["duplicate_evidence"] = evidence
    return out.drop(columns="_n")


def choose_canonical(df: pd.DataFrame) -> pd.DataFrame:
    """
    D-02: for an exact migration pair the helpdesk row wins.

    Reason: the current helpdesk is the system of record and already stores the
    reporting currency, so choosing it needs no conversion and cannot introduce a
    rounding error. Because all other columns are identical, the choice cannot
    change any non-money field - which is exactly why we verified that first.

    Conflicting pairs are NOT resolved. Both rows are kept and flagged.
    """
    out = df.copy()
    out["_prio"] = out.source_system.map(config.SOURCE_PRIORITY).fillna(9)
    is_pair = out.duplicate_status == "exact_migration_pair"

    rank = (out[is_pair].sort_values(["ticket_id", "_prio"])
            .groupby("ticket_id").cumcount())
    keep = pd.Series(True, index=out.index)
    keep.loc[rank[rank > 0].index] = False

    out["is_canonical"] = keep
    out["record_role"] = np.where(
        ~is_pair, "single_record",
        np.where(keep, "canonical_of_pair", "excluded_duplicate"),
    )
    return out.drop(columns="_prio")


def build_duplicate_audit(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per duplicate pair: both ticket ids, both source systems, both raw
    amounts, the observed ratio, which row was chosen and why.

    This is the audit trail the brief asks for. Nothing is deleted without
    appearing here.
    """
    pairs = df[df.duplicate_status.isin(("exact_migration_pair", "conflicting_pair"))]
    if pairs.empty:
        return pd.DataFrame(columns=[
            "ticket_id", "duplicate_status", "duplicate_confidence",
            "kept_source_system", "kept_amount_raw", "kept_amount_inr",
            "excluded_source_system", "excluded_amount_raw", "excluded_amount_inr",
            "observed_ratio", "amounts_reconcile", "duplicate_evidence",
        ])

    rows = []
    for tid, g in pairs.groupby("ticket_id"):
        kept = g[g.is_canonical]
        excl = g[~g.is_canonical]
        k = kept.iloc[0] if len(kept) else None
        e = excl.iloc[0] if len(excl) else None
        kr = None if k is None else k.refund_amount_raw
        er = None if e is None else e.refund_amount_raw
        ratio = (er / kr) if (kr and er and kr == kr and er == er and kr != 0) else np.nan
        ki = None if k is None else k.refund_amount_inr
        ei = None if e is None else e.refund_amount_inr
        reconcile = (
            "both blank" if (ki != ki and (ei is None or ei != ei))
            else ("yes" if (ki is not None and ei is not None and ki == ei) else "no")
        )
        rows.append({
            "ticket_id": tid,
            "duplicate_status": g.duplicate_status.iloc[0],
            "duplicate_confidence": g.duplicate_confidence.iloc[0],
            "kept_source_system": None if k is None else k.source_system,
            "kept_amount_raw": kr,
            "kept_amount_inr": ki,
            "excluded_source_system": None if e is None else e.source_system,
            "excluded_amount_raw": er,
            "excluded_amount_inr": ei,
            "observed_ratio": ratio,
            "amounts_reconcile": reconcile,
            "duplicate_evidence": g.duplicate_evidence.iloc[0],
        })
    return pd.DataFrame(rows)


def deduplicate(df: pd.DataFrame):
    """Detect, choose, and return (all_rows_tagged, canonical_rows, audit_table)."""
    tagged = choose_canonical(detect_duplicates(df))
    audit = build_duplicate_audit(tagged)
    canonical = tagged[tagged.is_canonical].copy()
    return tagged, canonical, audit
