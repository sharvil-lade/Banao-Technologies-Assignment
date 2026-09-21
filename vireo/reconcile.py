"""
Stage 10 - reconciliation.

This module exists because of one line in Arjun Mehta's email of 9 Sep:
"Rs 11 lakh a quarter versus my crore - one of us is reading the export wrong...
I want the total to reconcile."

The bridge walks from the raw export sum to the canonical total in named steps.
Its residual must be exactly zero, and the pipeline refuses to publish if it is not.
"""
from __future__ import annotations
import pandas as pd
from . import config


def build_bridge(normalised_all: pd.DataFrame, canonical_refunds: pd.DataFrame) -> pd.DataFrame:
    """
    Reconciliation bridge, one row per adjustment.

    Step 0 reproduces what a reader of the raw export gets by summing the column
    as exported - the number Finance is looking at.
    """
    raw_total = normalised_all.refund_amount_raw.sum()

    legacy = normalised_all[normalised_all.is_legacy]
    legacy_raw = legacy.refund_amount_raw.sum()
    legacy_inr = (legacy.refund_amount_raw / config.LEGACY_CONVERSION_FACTOR).sum()
    unit_adj = -(legacy_raw - legacy_inr)

    excluded = normalised_all[(~normalised_all.is_canonical) & normalised_all.has_refund]
    dup_adj = -excluded.refund_amount_inr.sum()

    canonical_total = canonical_refunds.refund_amount_inr.sum()

    rows = [
        {"step": "0. Raw export, refund_amount_inr summed as exported",
         "adjustment_inr": None, "running_total_inr": raw_total,
         "rows_affected": int(normalised_all.refund_amount_raw.notna().sum()),
         "why": "What a reader of the file gets with no handling. Matches the order of "
                "magnitude Finance reports."},
        {"step": "1. Legacy Freshdesk amounts converted from paise to rupees",
         "adjustment_inr": unit_adj, "running_total_inr": raw_total + unit_adj,
         "rows_affected": int(legacy.refund_amount_raw.notna().sum()),
         "why": f"policy S9: the legacy tool stored its own native unit. Measured factor "
                f"{config.LEGACY_CONVERSION_FACTOR} from 125 duplicate pairs, zero variance (D-03)."},
        {"step": "2. Migration duplicates removed (legacy twin of a re-imported ticket)",
         "adjustment_inr": dup_adj, "running_total_inr": raw_total + unit_adj + dup_adj,
         "rows_affected": int(len(excluded)),
         "why": "policy S9: a subset of legacy tickets was re-imported and appears under both "
                "source systems. The helpdesk row is kept (D-02); the twin is retained in "
                "duplicate_audit.csv, not deleted."},
        {"step": "3. Canonical refund total",
         "adjustment_inr": None, "running_total_inr": canonical_total,
         "rows_affected": int(len(canonical_refunds)),
         "why": "One row per ticket, all amounts in rupees."},
    ]
    return pd.DataFrame(rows)


def bridge_residual(bridge: pd.DataFrame) -> float:
    """Difference between the walked total and the canonical total. Must be 0.0."""
    walked = bridge.iloc[2].running_total_inr
    canonical = bridge.iloc[3].running_total_inr
    return float(round(walked - canonical, 2))


def aggregation_identities(canonical_refunds, monthly, reason, agent) -> pd.DataFrame:
    """
    The client's own test, made mechanical:
        sum(monthly) == sum(by reason) == sum(by agent) == canonical total.

    Any of these failing means a group-by dropped rows - usually a null key -
    which is the classic way a dashboard quietly under-reports.
    """
    total = canonical_refunds.refund_amount_inr.sum()
    checks = [
        ("sum(monthly) == canonical total", monthly.refund_amount_inr.sum(), total),
        ("sum(by reason code) == canonical total", reason.refund_amount_inr.sum(), total),
        ("sum(by agent) == canonical total", agent.refund_amount_inr.sum(), total),
        ("count(monthly) == canonical rows", monthly.refund_count.sum(), len(canonical_refunds)),
        ("count(by reason) == canonical rows", reason.refund_count.sum(), len(canonical_refunds)),
        ("count(by agent) == canonical rows", agent.refund_count.sum(), len(canonical_refunds)),
    ]
    return pd.DataFrame([
        {"identity": n, "computed": round(float(a), 2), "expected": round(float(b), 2),
         "difference": round(float(a) - float(b), 2),
         "result": "PASS" if abs(float(a) - float(b)) < 0.01 else "FAIL"}
        for n, a, b in checks
    ])


def client_number_comparison(canonical_refunds: pd.DataFrame) -> pd.DataFrame:
    """Put both client figures next to what the data actually supports."""
    q = (canonical_refunds.groupby("quarter").refund_amount_inr.sum())
    per_q = q.mean()
    return pd.DataFrame([
        {"source": "Arjun Mehta, Finance (email 7 & 9 Sep)",
         "claim": "well over Rs 1 crore per quarter",
         "reproducible_from_data": "yes - by summing the export without converting legacy paise",
         "per_quarter_inr": None},
        {"source": "Helpdesk standard report (via Sameer Qureshi, 7 Sep)",
         "claim": "around Rs 11 lakh per quarter",
         "reproducible_from_data": "yes - matches the canonical total",
         "per_quarter_inr": round(float(per_q))},
        {"source": "This pipeline",
         "claim": "canonical refund total",
         "reproducible_from_data": "reconciles to the raw export with zero residual",
         "per_quarter_inr": round(float(per_q))},
    ])
