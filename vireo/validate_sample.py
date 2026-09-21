"""
Independent verification of canonical records.

This module deliberately does NOT import the pipeline's transformation code.
It re-derives every field of a sampled canonical row straight from the raw CSV
with its own logic, then compares. Checking the pipeline by running the pipeline
proves nothing; two implementations disagreeing is informative.

Anything that disagrees is reported as a defect, not silently reconciled.
"""
from __future__ import annotations
import csv
import random
from collections import defaultdict
import pandas as pd
from . import config


def _raw_rows(path=None):
    """Read tickets.csv with the stdlib, not pandas - a second reader too."""
    with open(path or config.FILES["tickets"], newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def verify_sample(canonical: pd.DataFrame, n: int = 60, seed: int = 20260921,
                  raw_path=None, agents_path=None) -> tuple:
    """
    Re-derive n sampled canonical refund rows from scratch and compare.

    Returns (results_frame, summary_dict). Each check is independent, so one row
    can fail several checks and every failure is named.
    """
    raw = _raw_rows(raw_path)
    by_id = defaultdict(list)
    for r in raw:
        by_id[r["ticket_id"]].append(r)

    with open(agents_path or config.FILES["agents"], newline="", encoding="utf-8") as fh:
        roster = {a["agent_id"]: a for a in csv.DictReader(fh)}

    rng = random.Random(seed)
    ids = sorted(canonical.ticket_id)
    sample = rng.sample(ids, min(n, len(ids)))
    idx = canonical.set_index("ticket_id")

    results = []
    for tid in sample:
        got = idx.loc[tid]
        rows = by_id[tid]
        checks, notes = {}, []

        # -- the ticket exists in the raw export exactly as many times as expected
        checks["exists_in_raw"] = len(rows) >= 1
        expected_dup = "canonical_of_pair" if len(rows) == 2 else "single_record"
        checks["duplicate_status_correct"] = got.record_role == expected_dup

        # -- independent choice of which raw row is canonical
        if len(rows) == 2:
            chosen = next((r for r in rows if r["source_system"] == "helpdesk"), rows[0])
        else:
            chosen = rows[0]
        checks["source_system_correct"] = got.source_system == chosen["source_system"]

        # -- independent money derivation
        raw_amt = chosen["refund_amount_inr"]
        factor = 100 if chosen["source_system"] == "legacy_fd" else 1
        expected_inr = float(raw_amt) / factor if raw_amt else None
        checks["amount_correct"] = (
            expected_inr is not None and abs(float(got.refund_amount_inr) - expected_inr) < 0.005)
        checks["raw_amount_preserved"] = (
            raw_amt != "" and abs(float(got.refund_amount_raw) - float(raw_amt)) < 0.005)
        checks["conversion_factor_correct"] = int(got.conversion_factor) == factor
        if not checks["amount_correct"]:
            notes.append(f"amount {got.refund_amount_inr} != {expected_inr}")

        # -- independent month derivation from the raw string
        checks["month_correct"] = got.month == chosen["created_at"][:7]

        # -- reason code copied, never rewritten
        checks["reason_code_unchanged"] = got.reason_code == chosen["refund_reason_code"]

        # -- agent resolved from the roster
        ag = roster.get(chosen["agent_id"], {})
        checks["agent_id_correct"] = got.agent_id == chosen["agent_id"]
        checks["agent_name_correct"] = got.agent_name == ag.get("name")
        checks["agent_team_correct"] = got.agent_team == ag.get("team")

        # -- policy flags re-derived
        exp_conflict = (chosen["replacement_issued"] == "Y") and bool(raw_amt)
        checks["replacement_flag_correct"] = bool(got.flag_refund_and_replacement) == exp_conflict
        exp_cap = (chosen["refund_reason_code"] == "GW-OTHER"
                   and expected_inr is not None
                   and expected_inr > config.GOODWILL_CAP_INR)
        checks["goodwill_cap_flag_correct"] = bool(got.flag_goodwill_over_cap) == exp_cap
        exp_open = chosen["status"] in config.OPEN_STATUSES
        checks["open_flag_correct"] = bool(got.flag_ticket_open) == exp_open

        # -- the AI label never touched the money or the recorded code
        checks["ai_did_not_alter_fact"] = (
            got.reason_code == chosen["refund_reason_code"]
            and abs(float(got.refund_amount_inr) - (expected_inr or -1)) < 0.005)

        results.append({
            "ticket_id": tid, "source_system": got.source_system,
            "raw_amount": raw_amt, "canonical_amount": got.refund_amount_inr,
            "checks_run": len(checks), "checks_failed": sum(1 for v in checks.values() if not v),
            "failed_checks": ", ".join(k for k, v in checks.items() if not v),
            "row_correct": all(checks.values()), "notes": "; ".join(notes),
            **{f"chk_{k}": v for k, v in checks.items()},
        })

    df = pd.DataFrame(results)
    chk_cols = [c for c in df.columns if c.startswith("chk_")]
    summary = {
        "sample_size": len(df),
        "seed": seed,
        "rows_fully_correct": int(df.row_correct.sum()),
        "rows_with_any_error": int((~df.row_correct).sum()),
        "row_error_rate_pct": round((~df.row_correct).mean() * 100, 2),
        "field_checks_run": int(df.checks_run.sum()),
        "field_checks_failed": int(df.checks_failed.sum()),
        "field_error_rate_pct": round(df.checks_failed.sum() / max(df.checks_run.sum(), 1) * 100, 3),
        "checks_per_row": len(chk_cols),
    }
    per_check = {c[4:]: int((~df[c]).sum()) for c in chk_cols}
    summary["failures_by_check"] = {k: v for k, v in per_check.items() if v}
    return df, summary


def verify_totals_independently(canonical: pd.DataFrame, raw_path=None) -> pd.DataFrame:
    """
    Recompute the headline total from the raw file with stdlib only, no pandas,
    no pipeline. If this disagrees with canonical_refunds.csv, one of them is wrong.
    """
    raw = _raw_rows(raw_path)
    seen, total, count = {}, 0.0, 0
    for r in raw:
        tid = r["ticket_id"]
        prev = seen.get(tid)
        if prev is None or (prev["source_system"] == "legacy_fd" and r["source_system"] == "helpdesk"):
            seen[tid] = r
    for r in seen.values():
        if r["refund_amount_inr"]:
            total += float(r["refund_amount_inr"]) / (100 if r["source_system"] == "legacy_fd" else 1)
            count += 1
    pipe_total = float(canonical.refund_amount_inr.sum())
    return pd.DataFrame([
        {"check": "canonical refund total", "independent": round(total, 2),
         "pipeline": round(pipe_total, 2), "difference": round(total - pipe_total, 2),
         "result": "PASS" if abs(total - pipe_total) < 0.01 else "FAIL"},
        {"check": "canonical refund count", "independent": count,
         "pipeline": len(canonical), "difference": count - len(canonical),
         "result": "PASS" if count == len(canonical) else "FAIL"},
        {"check": "distinct canonical tickets", "independent": len(seen),
         "pipeline": None, "difference": None, "result": "INFO"},
    ])
