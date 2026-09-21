"""
Vireo refund reviewer - the smallest interface that lets someone check the work.

Run:  streamlit run app/app.py

Design rule, visible on every screen: anything computed from the source data is
labelled FACT; anything a model inferred from free text is labelled
INTERPRETATION and shown in a separate, marked block. A reader should never
have to wonder which they are looking at.
"""
from pathlib import Path
import sys
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DERIVED = ROOT / "data" / "derived"

st.set_page_config(page_title="Vireo refund review", layout="wide")


@st.cache_data
def load(name):
    return pd.read_csv(DERIVED / f"{name}.csv")


def inr(x):
    return f"₹{x:,.0f}"


try:
    refunds = load("canonical_refunds")
    tickets = load("canonical_tickets")
except FileNotFoundError:
    st.error("No pipeline output found. Run `python -m vireo.pipeline` first.")
    st.stop()

monthly = load("monthly_summary")
bridge = load("reconciliation_bridge")
identities = load("reconciliation_identities")
dup_audit = load("duplicate_audit")
by_agent = load("by_agent")
gw_check = load("goodwill_reality_check")
restated = load("by_reason_restated")
themes = load("by_theme")
ai_cov = load("ai_coverage")

st.title("Vireo Audio — monthly refunds")
st.caption("Who, how much, what for. Every figure traces to a source ticket.")

# ---------------------------------------------------------------- month filter
months = ["All months"] + sorted(refunds.month.unique())
col1, col2 = st.columns([1, 3])
with col1:
    month = st.selectbox("Month", months)
with col2:
    only_susp = st.checkbox("Suspicious cases only", value=False)

view = refunds if month == "All months" else refunds[refunds.month == month]
tview = tickets if month == "All months" else tickets[tickets.month == month]
if only_susp:
    view = view[view.is_suspicious]

a, b, c, d = st.columns(4)
a.metric("Refund value", inr(view.refund_amount_inr.sum()))
b.metric("Refunds", f"{len(view):,}")
c.metric("Refund rate", f"{len(view) / max(len(tview), 1) * 100:.1f}%")
d.metric("Suspicious", f"{int(view.is_suspicious.sum()):,}")

tabs = st.tabs(["Monthly", "Reason codes", "Agents", "What for (AI)",
                "Suspicious cases", "Records", "Reconciliation"])

# ------------------------------------------------------------------- monthly
with tabs[0]:
    st.subheader("FACT — monthly refund totals")
    st.caption("Computed from canonical_refunds.csv. Month = month the ticket was created (decision D-08).")
    st.bar_chart(monthly.set_index("month")["refund_amount_inr"])
    st.dataframe(monthly, use_container_width=True, hide_index=True)

# -------------------------------------------------------------- reason codes
with tabs[1]:
    st.subheader("FACT — refunds by the reason code the agent selected")
    r = (view.groupby(["reason_code", "reason_label"])
         .agg(refund_amount_inr=("refund_amount_inr", "sum"),
              refunds=("ticket_id", "size"),
              over_goodwill_cap=("flag_goodwill_over_cap", "sum")).reset_index())
    r["pct_of_value"] = (r.refund_amount_inr / max(view.refund_amount_inr.sum(), 1) * 100).round(1)
    st.dataframe(r.sort_values("refund_amount_inr", ascending=False),
                 use_container_width=True, hide_index=True)

    code = st.selectbox("Drill into a reason code", sorted(view.reason_code.unique()))
    sub = view[view.reason_code == code]
    st.write(f"**{len(sub)} refunds · {inr(sub.refund_amount_inr.sum())}**")
    st.dataframe(sub[["ticket_id", "month", "agent_name", "agent_team",
                      "refund_amount_inr", "ai_suggested_reason", "flag_evidence"]],
                 use_container_width=True, hide_index=True)

# ------------------------------------------------------------------- agents
with tabs[2]:
    st.subheader("FACT — refunds by agent, shown with exposure")
    st.warning(
        "Rupees alone are misleading here. Support policy §6 states the Returns Desk "
        "*processes the large majority of refunds by design*, and that Tier 2 agents "
        "are not to be compared with Tier 1 on volume. Read refund **rate** and "
        "tickets handled alongside the total, and compare within a team.",
        icon="⚠️")
    team = st.selectbox("Team", ["All teams"] + sorted(by_agent.agent_team.dropna().unique()))
    ag = by_agent if team == "All teams" else by_agent[by_agent.agent_team == team]
    st.dataframe(
        ag[["agent_id", "agent_name", "agent_team", "agent_tier", "tickets_handled",
            "refund_count", "refund_rate_pct", "refund_amount_inr", "avg_refund_inr",
            "gw_share_pct", "replacement_conflicts", "suspicious_count",
            "pct_of_total_refunds", "mean_csat"]],
        use_container_width=True, hide_index=True)
    st.caption("gw_share_pct = share of this agent's refund value booked to the dropdown "
               "default GW-OTHER. Comparable across agents doing similar work; a coaching "
               "signal, not an accusation.")

    agent = st.selectbox("Drill into an agent", sorted(view.agent_id.unique()))
    sub = view[view.agent_id == agent]
    st.write(f"**{sub.agent_name.iloc[0] if len(sub) else agent}** — "
             f"{len(sub)} refunds · {inr(sub.refund_amount_inr.sum())}")
    st.dataframe(sub[["ticket_id", "month", "reason_code", "refund_amount_inr",
                      "ai_suggested_reason", "flag_evidence"]],
                 use_container_width=True, hide_index=True)

# --------------------------------------------------------------- what for AI
with tabs[3]:
    st.subheader("INTERPRETATION — what the free text says the refund was for")
    st.info(
        "Everything on this tab is a model's reading of `customer_message` and "
        "`agent_notes`. The recorded reason code is never overwritten (decision D-16); "
        "the amounts are still computed in pandas. Measured accuracy and the known "
        "failure modes are in docs/validation.md.", icon="🤖")

    st.markdown("#### The dropdown-default problem")
    gw_value = refunds[refunds.reason_code == "GW-OTHER"].refund_amount_inr.sum()
    genuine = gw_check[gw_check.is_genuine_goodwill].amount_inr.sum() if len(gw_check) else 0
    x, y = st.columns(2)
    x.metric("Booked as Goodwill / Other", inr(gw_value))
    y.metric("Text actually supports goodwill", inr(genuine),
             delta=f"-{inr(gw_value - genuine)} is something else", delta_color="inverse")
    st.dataframe(gw_check, use_container_width=True, hide_index=True)

    st.markdown("#### Recorded code vs restated code")
    st.dataframe(restated, use_container_width=True, hide_index=True)

    st.markdown("#### Underlying driver")
    st.dataframe(themes, use_container_width=True, hide_index=True)

    st.markdown("#### How each label was produced")
    st.dataframe(ai_cov, use_container_width=True, hide_index=True)
    st.caption("Only rows marked costs_money=True required a model call.")

# ---------------------------------------------------------- suspicious cases
with tabs[4]:
    st.subheader("FACT — suspicious cases, each with its evidence")
    flags = {
        "Refund + replacement (flagged)": "flag_refund_and_replacement",
        "Refund + replacement (only in the note)": "flag_refund_and_replacement_text",
        "Goodwill above the ₹500 cap": "flag_goodwill_over_cap",
        "Refund exceeds order value": "flag_refund_exceeds_order",
        "Refund on an open/pending ticket": "flag_ticket_open",
    }
    pick = st.multiselect("Flags", list(flags), default=list(flags)[:2])
    if pick:
        mask = view[[flags[p] for p in pick]].any(axis=1)
        sub = view[mask]
    else:
        sub = view[view.is_suspicious]
    st.write(f"**{len(sub)} tickets · {inr(sub.refund_amount_inr.sum())} in refunds · "
             f"{inr(sub.conflict_total_cost_inr.sum())} total cost incl. replacements**")
    st.dataframe(sub[["ticket_id", "month", "agent_name", "agent_team", "reason_code",
                      "refund_amount_inr", "replacement_conflict_source",
                      "replacement_text_quote", "flag_evidence"]],
                 use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ records
with tabs[5]:
    st.subheader("Inspect a single refund against its source record")
    tid = st.selectbox("Ticket", sorted(view.ticket_id.unique()))
    r = refunds[refunds.ticket_id == tid].iloc[0]
    l, rgt = st.columns(2)
    with l:
        st.markdown("**FACT — from the source system**")
        st.write({
            "ticket_id": r.ticket_id, "month": r.month, "status": r.status,
            "agent": f"{r.agent_name} ({r.agent_id}), {r.agent_team}, tier {r.agent_tier}",
            "recorded reason": f"{r.reason_code} — {r.reason_label}",
            "refund (normalised)": inr(r.refund_amount_inr),
            "refund (as exported)": f"{r.refund_amount_raw:,.0f} {r.currency_unit_source}",
            "conversion factor": r.conversion_factor,
            "source system": r.source_system,
            "duplicate status": r.duplicate_status,
            "order match": r.order_match,
            "order value": inr(r.order_value_inr) if pd.notna(r.order_value_inr) else "not attached",
            "product": f"{r.product_name} ({r.product_sku})",
        })
        if r.flag_count:
            st.error(f"**{int(r.flag_count)} flag(s):** {r.flag_evidence}")
    with rgt:
        st.markdown("**INTERPRETATION — from the free text**")
        st.write({
            "restated reason": r.ai_suggested_reason,
            "theme": r.ai_theme,
            "confidence": r.ai_confidence,
            "quoted evidence": r.ai_evidence_quote,
            "label source": r.ai_run_id,
            "model": r.ai_model,
            "disagrees with recorded code": bool(r.flag_reason_mismatch),
        })
    st.markdown("**Source text**")
    st.text_area("Customer message", r.customer_message, height=120)
    st.text_area("Agent closing note", r.agent_notes, height=100)
    if r.duplicate_status == "canonical_of_pair":
        st.markdown("**Duplicate audit — the row that was excluded**")
        st.dataframe(dup_audit[dup_audit.ticket_id == tid], hide_index=True)

# ----------------------------------------------------------- reconciliation
with tabs[6]:
    st.subheader("FACT — how the raw export becomes the canonical total")
    st.caption("Arjun Mehta, 9 Sep: “I want the total to reconcile.” This is that.")
    st.dataframe(bridge, use_container_width=True, hide_index=True)
    residual = bridge.iloc[2].running_total_inr - bridge.iloc[3].running_total_inr
    st.success(f"Residual: {inr(residual)} — the bridge closes exactly.")
    st.dataframe(identities, use_container_width=True, hide_index=True)
    st.markdown("#### Duplicate audit (every excluded row is retained here)")
    st.dataframe(dup_audit.head(200), use_container_width=True, hide_index=True)
