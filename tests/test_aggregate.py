"""Monthly, reason and agent aggregation."""
import pandas as pd
from vireo import aggregate, canonical
from conftest import ticket, frame


def _tbl(make_canonical, rows):
    refunds, canon, _ = make_canonical(rows)
    return refunds, canonical.build_canonical_tickets(canon)


def test_monthly_totals_and_rate(make_canonical):
    rows = [
        ticket(ticket_id="TK-1", created_at="2025-03-04 10:00",
               refund_amount_inr="1000", refund_reason_code="CANCEL"),
        ticket(ticket_id="TK-2", created_at="2025-03-20 10:00",
               refund_amount_inr="500", refund_reason_code="CANCEL"),
        ticket(ticket_id="TK-3", created_at="2025-03-25 10:00"),        # no refund
        ticket(ticket_id="TK-4", created_at="2025-04-02 10:00",
               refund_amount_inr="250", refund_reason_code="PRICE-ADJ"),
    ]
    refunds, tickets = _tbl(make_canonical, rows)
    m = aggregate.monthly_summary(refunds, tickets).set_index("month")
    assert m.loc["2025-03", "refund_amount_inr"] == 1500
    assert m.loc["2025-03", "refund_count"] == 2
    assert m.loc["2025-03", "tickets_total"] == 3
    assert m.loc["2025-03", "refund_rate_pct"] == 66.7
    assert m.loc["2025-04", "refund_amount_inr"] == 250


def test_a_month_with_no_refunds_does_not_invent_one(make_canonical):
    refunds, tickets = _tbl(make_canonical, [
        ticket(ticket_id="TK-1", created_at="2025-03-04 10:00"),
        ticket(ticket_id="TK-2", created_at="2025-04-04 10:00",
               refund_amount_inr="100", refund_reason_code="CANCEL")])
    m = aggregate.monthly_summary(refunds, tickets)
    assert list(m.month) == ["2025-04"]


def test_reason_shares_sum_to_100(make_canonical):
    refunds, _ = _tbl(make_canonical, [
        ticket(ticket_id="TK-1", refund_amount_inr="750", refund_reason_code="GW-OTHER"),
        ticket(ticket_id="TK-2", refund_amount_inr="250", refund_reason_code="CANCEL")])
    r = aggregate.by_reason(refunds).set_index("reason_code")
    assert r.loc["GW-OTHER", "pct_of_refund_value"] == 75.0
    assert round(r.pct_of_refund_value.sum()) == 100


def test_agent_view_carries_exposure_not_just_rupees(make_canonical):
    """
    D-15: rupees alone would name the Returns Desk. The agent table must show
    tickets handled and refund rate so a reader can see why the rupees are high.
    """
    rows = [ticket(ticket_id=f"TK-{i}", agent_id="A3036",
                   refund_amount_inr="1000", refund_reason_code="GW-OTHER")
            for i in range(3)]
    rows += [ticket(ticket_id=f"TK-1{i}", agent_id="A3036") for i in range(7)]
    rows += [ticket(ticket_id="TK-99", agent_id="A3001",
                    refund_amount_inr="1000", refund_reason_code="CANCEL")]
    refunds, tickets = _tbl(make_canonical, rows)
    a = aggregate.by_agent(refunds, tickets).set_index("agent_id")
    assert a.loc["A3036", "refund_amount_inr"] == 3000
    assert a.loc["A3036", "tickets_handled"] == 10
    assert a.loc["A3036", "refund_rate_pct"] == 30.0
    assert a.loc["A3036", "gw_share_pct"] == 100.0
    assert a.loc["A3001", "refund_rate_pct"] == 100.0   # 1 ticket, 1 refund
    assert a.loc["A3001", "gw_share_pct"] == 0.0
    assert set(a.columns) >= {"agent_team", "agent_tier", "tickets_handled",
                              "refund_rate_pct", "pct_of_total_refunds"}


def test_aggregation_identities_hold(make_canonical):
    from vireo import reconcile
    rows = [ticket(ticket_id=f"TK-{i}", agent_id="A3036" if i % 2 else "A3001",
                   created_at=f"2025-0{(i % 3) + 1}-04 10:00",
                   refund_amount_inr=str(100 * (i + 1)),
                   refund_reason_code="GW-OTHER" if i % 2 else "CANCEL")
            for i in range(10)]
    refunds, tickets = _tbl(make_canonical, rows)
    ident = reconcile.aggregation_identities(
        refunds, aggregate.monthly_summary(refunds, tickets),
        aggregate.by_reason(refunds), aggregate.by_agent(refunds, tickets))
    assert (ident.result == "PASS").all()


def test_open_ticket_refund_reaches_the_monthly_total(make_canonical):
    """D-10 end to end: an open ticket's refund must not vanish in aggregation."""
    refunds, tickets = _tbl(make_canonical, [
        ticket(ticket_id="TK-1", status="open", resolved_at="",
               created_at="2025-05-04 10:00", refund_amount_inr="5524",
               refund_reason_code="RETURN-QC-OK")])
    m = aggregate.monthly_summary(refunds, tickets)
    assert m.iloc[0].refund_amount_inr == 5524
