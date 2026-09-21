"""
Stage 3 - normalisation.

Every transformation here keeps the value it started from, so any number in the
final report can be walked back to the exported cell it came from.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config


def normalise_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse the three timestamps. No timezone conversion is applied.

    D-09: policy S9 warns the API exports UTC and legacy resolved_at was
    reconstructed from a UTC event log, but this export is the standard report,
    which S9 says displays IST, and validate_timestamp_ordering finds zero
    negative durations in either system. Converting anything here would
    manufacture the error we set out to avoid.
    """
    out = df.copy()
    for col in ("created_at", "first_response_at", "resolved_at"):
        out[col + "_ts"] = pd.to_datetime(out[col].replace("", None), errors="coerce")
    out["month"] = out.created_at_ts.dt.strftime("%Y-%m")            # D-08 primary basis
    out["month_resolved"] = out.resolved_at_ts.dt.strftime("%Y-%m")  # D-08 alternative
    out["quarter"] = (
        out.created_at_ts.dt.year.astype("Int64").astype(str)
        + "Q" + out.created_at_ts.dt.quarter.astype("Int64").astype(str)
    )
    return out


def identify_source_system(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each row with its money unit and whether it predates the helpdesk go-live.

    The unit is driven by source_system alone, never by the size of the number -
    a rule based on magnitude would misclassify a genuinely large rupee refund.
    """
    out = df.copy()
    out["is_legacy"] = out.source_system == "legacy_fd"
    out["currency_unit_source"] = np.where(out.is_legacy, "paise", "INR")
    out["conversion_factor"] = np.where(out.is_legacy, config.LEGACY_CONVERSION_FACTOR, 1)
    out["pre_golive"] = out.created_at_ts < pd.Timestamp(config.HELPDESK_GOLIVE)
    return out


def normalise_refund_amount(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert refund amounts to rupees.

    D-03: legacy_fd stores paise. Measured, not assumed: across the 125 duplicate
    pairs that carry an amount on both sides, legacy / helpdesk = 100.0 in 125 of
    125 cases with zero variance, and 775 of 775 legacy amounts are divisible
    by 100. `verify_legacy_conversion` below re-proves this on every run.
    """
    out = df.copy()
    out["refund_amount_raw"] = pd.to_numeric(
        out.refund_amount_inr.replace("", None), errors="coerce"
    )
    out["refund_amount_inr"] = out.refund_amount_raw / out.conversion_factor
    out["has_refund"] = out.refund_amount_inr.notna()
    return out


def verify_legacy_conversion(df: pd.DataFrame) -> dict:
    """
    Re-derive the legacy conversion factor from the data itself.

    Returns the observed ratio distribution across duplicate pairs. The pipeline
    aborts if the measured factor stops matching config, so a future export with
    a different legacy unit fails loudly rather than silently mis-stating money.
    """
    dup = df[df.ticket_id.duplicated(keep=False)]
    piv = dup.pivot_table(index="ticket_id", columns="source_system",
                          values="refund_amount_raw", aggfunc="first")
    if not {"helpdesk", "legacy_fd"}.issubset(piv.columns):
        return {"pairs_observed": 0, "factor": None, "unanimous": False}
    both = piv.dropna()
    if both.empty:
        return {"pairs_observed": 0, "factor": None, "unanimous": False}
    ratio = (both.legacy_fd / both.helpdesk).round(6)
    counts = ratio.value_counts()
    return {
        "pairs_observed": int(len(both)),
        "factor": float(counts.index[0]),
        "unanimous": bool(len(counts) == 1),
        "ratio_std": float(ratio.std()),
        "legacy_divisible_by_100_pct": float(
            (df.loc[df.is_legacy & df.refund_amount_raw.notna(), "refund_amount_raw"]
             % 100 == 0).mean() * 100
        ),
    }


def normalise_reason_code(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach the policy S5 label. The recorded code is never rewritten (D-16).

    An unrecognised code is labelled UNKNOWN and flagged; the row is kept, so a
    dropdown change at Vireo shows up as a visible flag rather than a silent
    hole in the totals.
    """
    out = df.copy()
    code = out.refund_reason_code.fillna("").str.strip().str.upper()
    out["reason_code"] = code
    out["reason_label"] = code.map(config.REASON_LABELS)
    out["unknown_reason_code"] = out.has_refund & ~code.isin(config.REASON_LABELS)
    out.loc[out.unknown_reason_code, "reason_label"] = "UNKNOWN"
    out["reason_is_dropdown_default"] = code == config.DROPDOWN_DEFAULT_REASON
    return out


def normalise_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Booleans and numerics that the rest of the pipeline relies on."""
    out = df.copy()
    out["replacement_flag"] = out.replacement_issued.str.strip().str.upper() == "Y"
    out["ticket_open"] = out.status.isin(config.OPEN_STATUSES)
    out["transfers_n"] = pd.to_numeric(out.transfers.replace("", None), errors="coerce").fillna(0).astype(int)
    # Policy S8: a blank CSAT is "no response" and must be excluded from averages,
    # not treated as zero. NaN does exactly that in every pandas aggregation.
    out["csat"] = pd.to_numeric(out.csat_score.replace("", None), errors="coerce")
    return out


def normalise(tickets: pd.DataFrame) -> pd.DataFrame:
    """Run the full normalisation chain in order."""
    df = normalise_timestamps(tickets)
    df = identify_source_system(df)
    df = normalise_refund_amount(df)
    df = normalise_reason_code(df)
    df = normalise_flags(df)
    return df
