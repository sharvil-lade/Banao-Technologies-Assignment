"""Order/customer/product joins and roster resolution."""
import pandas as pd
import pytest
from vireo import normalise, joins, agents as agents_mod, load
from conftest import ticket, frame


@pytest.fixture(scope="module")
def raw():
    return load.load_all()


def test_direct_order_join(raw):
    df = joins.attach_orders(normalise.normalise(frame([
        ticket(ticket_id="TK-1", order_id="VR880597")])), raw["orders"])
    assert df.iloc[0].order_match == "direct"
    assert df.iloc[0].order_value_inr > 0


def test_fallback_unique_join_attaches_context(raw):
    """E7: exactly one candidate order for this customer+SKU."""
    orders = pd.DataFrame([{"order_id": "VR000001", "customer_id": "C100000",
                            "sku": "VA-EB-PL1", "order_date": "2025-01-01",
                            "channel": "Amazon", "qty": "1",
                            "order_value_inr": "2499", "lot_code": "L1"}])
    df = joins.attach_orders(normalise.normalise(frame([
        ticket(ticket_id="TK-2", order_id="", customer_id="C100000",
               product_sku="VA-EB-PL1")])), orders)
    r = df.iloc[0]
    assert r.order_match == "fallback_unique"
    assert r.order_id == "VR000001"
    assert r.order_value_inr == 2499.0


def test_ambiguous_fallback_attaches_nothing(raw):
    """E8: two candidates means we invent nothing (D-06)."""
    orders = pd.DataFrame([
        {"order_id": "VR000001", "customer_id": "C100000", "sku": "VA-EB-PL1",
         "order_date": "2025-01-01", "channel": "Amazon", "qty": "1",
         "order_value_inr": "2499", "lot_code": "L1"},
        {"order_id": "VR000002", "customer_id": "C100000", "sku": "VA-EB-PL1",
         "order_date": "2025-02-01", "channel": "Amazon", "qty": "1",
         "order_value_inr": "1999", "lot_code": "L2"},
    ])
    df = joins.attach_orders(normalise.normalise(frame([
        ticket(ticket_id="TK-3", order_id="", customer_id="C100000",
               product_sku="VA-EB-PL1")])), orders)
    r = df.iloc[0]
    assert r.order_match == "ambiguous"
    assert r.order_candidates == 2
    assert r.order_id == ""
    assert pd.isna(r.order_value_inr)


def test_ambiguous_join_does_not_change_the_refund(raw):
    """The safety property behind D-06: context can be missing, money cannot move."""
    orders = pd.DataFrame([
        {"order_id": "VR1", "customer_id": "C100000", "sku": "VA-EB-PL1",
         "order_date": "2025-01-01", "channel": "Amazon", "qty": "1",
         "order_value_inr": "2499", "lot_code": "L1"},
        {"order_id": "VR2", "customer_id": "C100000", "sku": "VA-EB-PL1",
         "order_date": "2025-02-01", "channel": "Amazon", "qty": "1",
         "order_value_inr": "1999", "lot_code": "L2"},
    ])
    t = normalise.normalise(frame([ticket(
        ticket_id="TK-4", order_id="", refund_amount_inr="1500",
        refund_reason_code="CANCEL")]))
    before = t.refund_amount_inr.sum()
    after = joins.attach_orders(t, orders).refund_amount_inr.sum()
    assert before == after == 1500.0


def test_join_never_changes_row_count(raw):
    t = normalise.normalise(load.load_tickets())
    assert len(joins.attach_orders(t, raw["orders"])) == len(t)


def test_roster_lookup_single_row(raw):
    df = agents_mod.attach_agents(
        normalise.normalise(frame([ticket(ticket_id="TK-5", agent_id="A3036")])),
        raw["agents"])
    assert df.iloc[0].agent_name == "Ritika D'Souza"
    assert df.iloc[0].agent_team == "Returns Desk"
    assert df.iloc[0].roster_match == "in_force"


def test_roster_picks_the_assignment_in_force_on_the_ticket_date():
    """
    D-07: not exercised by today's data, which has one row per agent. Built and
    tested anyway because the naive join's failure mode is silent row
    duplication that would inflate every agent total.
    """
    roster = pd.DataFrame([
        {"agent_id": "A9", "name": "Test Agent", "site": "Indore", "team": "Billing",
         "shift": "Day", "tier": "1", "from_date": "2024-01-01", "to_date": "2025-06-30"},
        {"agent_id": "A9", "name": "Test Agent", "site": "Bengaluru", "team": "Returns Desk",
         "shift": "Night", "tier": "1", "from_date": "2025-07-01", "to_date": ""},
    ])
    t = normalise.normalise(frame([
        ticket(ticket_id="TK-6", agent_id="A9", created_at="2025-03-04 10:00"),
        ticket(ticket_id="TK-7", agent_id="A9", created_at="2025-09-04 10:00"),
    ]))
    df = agents_mod.attach_agents(t, roster)
    assert len(df) == 2, "overlapping roster rows must not fan out the ticket table"
    assert df.set_index("ticket_id").loc["TK-6", "agent_team"] == "Billing"
    assert df.set_index("ticket_id").loc["TK-7", "agent_team"] == "Returns Desk"


def test_ticket_outside_roster_dates_is_kept_not_dropped():
    roster = pd.DataFrame([{
        "agent_id": "A9", "name": "Test Agent", "site": "Indore", "team": "Billing",
        "shift": "Day", "tier": "1", "from_date": "2026-01-01", "to_date": ""}])
    t = normalise.normalise(frame([ticket(
        ticket_id="TK-8", agent_id="A9", created_at="2025-03-04 10:00",
        refund_amount_inr="900", refund_reason_code="CANCEL")]))
    df = agents_mod.attach_agents(t, roster)
    assert len(df) == 1
    assert df.iloc[0].roster_match == "outside_roster_dates_earliest_used"
    assert df.iloc[0].refund_amount_inr == 900.0
