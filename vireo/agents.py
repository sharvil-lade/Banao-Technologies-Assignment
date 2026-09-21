"""
Stage 5 - agent / roster resolution.

D-07: in this extract every agent has exactly one roster row and every to_date is
blank, so a plain lookup would work today. We implement the date-ranged version
anyway - about fifteen extra lines - because the data-pack README says an agent
can have more than one row, and the failure mode of the naive version is silent
row duplication that would inflate every agent total. Cheap insurance, tested.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from . import config


def prepare_roster(agents: pd.DataFrame) -> pd.DataFrame:
    out = agents.copy()
    out["from_ts"] = pd.to_datetime(out.from_date.replace("", None), errors="coerce")
    out["to_ts"] = pd.to_datetime(out.to_date.replace("", None), errors="coerce")
    # A blank from_date means "always"; a blank to_date means "still current".
    out["from_ts"] = out.from_ts.fillna(pd.Timestamp.min)
    out["to_ts"] = out.to_ts.fillna(pd.Timestamp.max)
    out["tier"] = out.tier.astype(str)
    out["is_tier2"] = out.team.isin(config.TIER2_TEAMS) | (out.tier == "2")
    return out


def resolve_agent(roster: pd.DataFrame, agent_id: str, as_of) -> dict:
    """
    The roster row in force for this agent on this date.

    If several rows overlap the date, the one with the latest from_date wins
    (the most recent assignment). If none covers the date - e.g. a ticket
    resolved before the agent's recorded start - we fall back to the earliest
    row and mark it, rather than dropping the agent and losing the refund.
    """
    as_of = pd.Timestamp(as_of)
    cand = roster[roster.agent_id == agent_id]
    if cand.empty:
        return {"agent_id": agent_id, "agent_name": None, "agent_team": None,
                "agent_tier": None, "agent_site": None, "agent_shift": None,
                "roster_match": "not_in_roster"}
    live = cand[(cand.from_ts <= as_of) & (cand.to_ts >= as_of)]
    if len(live):
        row = live.sort_values("from_ts").iloc[-1]
        match = "in_force" if len(live) == 1 else "overlapping_rows_latest_used"
    else:
        row = cand.sort_values("from_ts").iloc[0]
        match = "outside_roster_dates_earliest_used"
    return {"agent_id": agent_id, "agent_name": row["name"], "agent_team": row.team,
            "agent_tier": row.tier, "agent_site": row.site, "agent_shift": row.shift,
            "roster_match": match}


def attach_agents(tickets: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorised, date-ranged roster join.

    Deliberately NOT a plain merge. A plain merge on agent_id fans out one ticket
    into one row per roster assignment, which would silently multiply that
    agent's refunds. Here every ticket resolves to exactly one roster row, and
    the row count is asserted afterwards.
    """
    roster = prepare_roster(agents)
    out = tickets.copy().reset_index(drop=True)
    n_before = len(out)
    out["_i"] = range(len(out))

    m = out[["_i", "agent_id", "created_at_ts"]].merge(roster, on="agent_id", how="left")
    in_force = (m.from_ts <= m.created_at_ts) & (m.to_ts >= m.created_at_ts)

    live = m[in_force].sort_values(["_i", "from_ts"])
    n_live = live.groupby("_i").size()
    chosen = live.groupby("_i").tail(1).set_index("_i")
    chosen["roster_match"] = np.where(
        n_live.reindex(chosen.index).to_numpy() > 1,
        "overlapping_rows_latest_used", "in_force")

    # A ticket whose date falls outside every assignment still has a real agent
    # and a real refund. Fall back to the earliest row and say so, rather than
    # dropping the ticket and losing the money.
    missing = set(out["_i"]) - set(chosen.index)
    if missing:
        fb = (m[m["_i"].isin(missing) & m["name"].notna()]
              .sort_values(["_i", "from_ts"]).groupby("_i").head(1).set_index("_i"))
        fb["roster_match"] = "outside_roster_dates_earliest_used"
        chosen = pd.concat([chosen, fb])

    chosen = chosen.reindex(out["_i"])
    out["agent_name"] = chosen["name"].to_numpy()
    out["agent_team"] = chosen["team"].to_numpy()
    out["agent_tier"] = chosen["tier"].to_numpy()
    out["agent_site"] = chosen["site"].to_numpy()
    out["agent_shift"] = chosen["shift"].to_numpy()
    out["roster_match"] = pd.Series(chosen["roster_match"].to_numpy()).fillna("not_in_roster").to_numpy()
    out = out.drop(columns="_i")

    assert len(out) == n_before, "roster join changed the row count - overlapping assignments"
    out["agent_is_tier2"] = out.agent_tier.astype(str) == "2"
    # Policy S6: the Returns Desk processes most refunds by design. Carried as a
    # column so the UI can show exposure rather than let rupees speak alone (D-15).
    out["agent_team_owns_refunds"] = out.agent_team.isin(config.REFUND_OWNING_TEAMS)
    return out
