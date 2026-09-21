"""
Stage 9 - aggregation.

Plain deterministic group-bys over the canonical table. No LLM ever touches a
number in this module; that separation is the whole point of the architecture.
"""
from __future__ import annotations
import pandas as pd


def monthly_summary(refunds: pd.DataFrame, tickets: pd.DataFrame | None = None,
                    month_col: str = "month") -> pd.DataFrame:
    g = refunds.groupby(month_col, dropna=False)
    out = g.agg(refund_amount_inr=("refund_amount_inr", "sum"),
                refund_count=("ticket_id", "size"),
                median_refund_inr=("refund_amount_inr", "median"),
                suspicious_count=("is_suspicious", "sum"),
                replacement_conflicts=("flag_replacement_conflict_any", "sum"),
                goodwill_over_cap=("flag_goodwill_over_cap", "sum")).reset_index()
    if tickets is not None:
        vol = tickets.groupby("month").size().rename("tickets_total")
        out = out.merge(vol, left_on=month_col, right_index=True, how="left")
        out["refund_rate_pct"] = (out.refund_count / out.tickets_total * 100).round(1)
        out["refund_per_ticket_inr"] = (out.refund_amount_inr / out.tickets_total).round(0)
    return out.sort_values(month_col).reset_index(drop=True)


def by_reason(refunds: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    total = refunds.refund_amount_inr.sum()
    out = (refunds.groupby(["reason_code", "reason_label"])
           .agg(refund_amount_inr=("refund_amount_inr", "sum"),
                refund_count=("ticket_id", "size"),
                median_refund_inr=("refund_amount_inr", "median"),
                over_goodwill_cap=("flag_goodwill_over_cap", "sum"))
           .reset_index())
    out["pct_of_refund_value"] = (out.refund_amount_inr / total * 100).round(1)
    return out.sort_values("refund_amount_inr", ascending=False).reset_index(drop=True)


def by_reason_month(refunds: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    return (refunds.pivot_table(index=month_col, columns="reason_code",
                                values="refund_amount_inr", aggfunc="sum")
            .fillna(0).round(0).reset_index())


def by_agent(refunds: pd.DataFrame, tickets: pd.DataFrame) -> pd.DataFrame:
    """
    Agent view, deliberately not a league table (D-15).

    Policy S6 says the Returns Desk processes most refunds by design and that
    Tier 2 must not be compared with Tier 1 on volume. So every agent row
    carries the exposure that explains its rupees: tickets handled, refund rate,
    team, tier. `gw_share_pct` is the comparable signal - how often this agent
    reaches for the dropdown default when raising a refund.
    """
    total = refunds.refund_amount_inr.sum()
    a = (refunds.groupby("agent_id")
         .agg(refund_amount_inr=("refund_amount_inr", "sum"),
              refund_count=("ticket_id", "size"),
              avg_refund_inr=("refund_amount_inr", "mean"),
              suspicious_count=("is_suspicious", "sum"),
              replacement_conflicts=("flag_replacement_conflict_any", "sum"),
              goodwill_over_cap=("flag_goodwill_over_cap", "sum"),
              agent_name=("agent_name", "first"), agent_team=("agent_team", "first"),
              agent_tier=("agent_tier", "first"), agent_site=("agent_site", "first"),
              agent_is_tier2=("agent_is_tier2", "first"))
         .reset_index())

    vol = tickets.groupby("agent_id").agg(tickets_handled=("ticket_id", "size"),
                                          mean_csat=("csat", "mean")).reset_index()
    a = a.merge(vol, on="agent_id", how="left")

    gw = (refunds[refunds.reason_code == "GW-OTHER"].groupby("agent_id")
          .refund_amount_inr.sum().rename("gw_amount_inr"))
    a = a.merge(gw, on="agent_id", how="left")
    a["gw_amount_inr"] = a.gw_amount_inr.fillna(0)

    a["refund_rate_pct"] = (a.refund_count / a.tickets_handled * 100).round(1)
    a["pct_of_total_refunds"] = (a.refund_amount_inr / total * 100).round(1)
    a["gw_share_pct"] = (a.gw_amount_inr / a.refund_amount_inr * 100).round(1)
    a["avg_refund_inr"] = a.avg_refund_inr.round(0)
    a["mean_csat"] = a.mean_csat.round(2)   # policy S8: blanks excluded, not zeroed
    return a.sort_values("refund_amount_inr", ascending=False).reset_index(drop=True)


def by_team(refunds: pd.DataFrame, tickets: pd.DataFrame) -> pd.DataFrame:
    t = (refunds.groupby("agent_team")
         .agg(refund_amount_inr=("refund_amount_inr", "sum"),
              refund_count=("ticket_id", "size"),
              replacement_conflicts=("flag_replacement_conflict_any", "sum"))
         .reset_index())
    vol = tickets.groupby("agent_team").size().rename("tickets_handled")
    t = t.merge(vol, on="agent_team", how="left")
    t["refund_rate_pct"] = (t.refund_count / t.tickets_handled * 100).round(1)
    return t.sort_values("refund_amount_inr", ascending=False).reset_index(drop=True)


def suspicious_cases(refunds: pd.DataFrame) -> pd.DataFrame:
    cols = ["ticket_id", "month", "agent_id", "agent_name", "agent_team", "reason_code",
            "refund_amount_inr", "replacement_conflict_source", "replacement_text_quote",
            "flag_evidence", "flag_count", "source_system", "order_id", "product_sku",
            "customer_message", "agent_notes"]
    out = refunds[refunds.is_suspicious][cols].copy()
    return out.sort_values(["flag_count", "refund_amount_inr"], ascending=False).reset_index(drop=True)
