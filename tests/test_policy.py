"""Policy flags: refund+replacement, goodwill cap, outliers, open tickets."""
import pandas as pd
from vireo import normalise, policy, joins, agents as agents_mod, load, dedupe
from conftest import ticket, frame


def _prep(rows):
    raw = load.load_all()
    t = normalise.normalise(frame(rows))
    _, t, _ = dedupe.deduplicate(t)
    t = agents_mod.attach_agents(t, raw["agents"])
    t = joins.attach_all(t, raw["orders"], raw["products"], raw["customers"])
    return policy.apply_policy(t)


def test_refund_and_replacement_flagged_from_the_structured_field():
    """E9: policy S5 forbids both. replacement_issued=Y plus a refund is a breach."""
    df = _prep([ticket(ticket_id="TK-1", refund_amount_inr="1999",
                       refund_reason_code="GW-OTHER", replacement_issued="Y")])
    r = df.iloc[0]
    assert bool(r.flag_refund_and_replacement)
    assert bool(r.flag_replacement_conflict_any)
    assert r.replacement_conflict_source == "flag_only"
    assert "policy S5" in r.flag_evidence


def test_refund_and_replacement_found_in_the_note_when_the_flag_says_no():
    """E10: the structured flag under-reports; the agent's own note gives it away."""
    df = _prep([ticket(ticket_id="TK-2", refund_amount_inr="3499",
                       refund_reason_code="WTY-BUYBACK", replacement_issued="N",
                       agent_notes="Advised, cx will monitor. Issued refund + replacement both, TL aware. -KS")])
    r = df.iloc[0]
    assert not bool(r.flag_refund_and_replacement)
    assert bool(r.flag_refund_and_replacement_text)
    assert r.replacement_conflict_source == "note_only"
    assert "refund + replacement" in r.replacement_text_quote.lower()


def test_a_plain_replacement_mention_is_not_a_conflict():
    """Precision guard: the detector must not fire on ordinary replacement prose."""
    df = _prep([ticket(ticket_id="TK-3", refund_amount_inr="1200",
                       refund_reason_code="DOA-REPL", replacement_issued="N",
                       agent_notes="rplc unit dispatched under DOA, no refund needed beyond this")])
    assert not bool(df.iloc[0].flag_refund_and_replacement_text)


def test_no_refund_means_no_conflict_even_with_a_replacement():
    """A replacement on its own is normal policy, not a breach."""
    df = _prep([ticket(ticket_id="TK-4", refund_amount_inr="", refund_reason_code="",
                       replacement_issued="Y")])
    assert not bool(df.iloc[0].flag_replacement_conflict_any)


def test_replacement_cost_model_follows_policy_s5():
    """unit_cost + Rs 340. VA-EB-PL1 unit cost is Rs 1,120."""
    df = _prep([ticket(ticket_id="TK-5", product_sku="VA-EB-PL1",
                       refund_amount_inr="2499", refund_reason_code="GW-OTHER",
                       replacement_issued="Y")])
    r = df.iloc[0]
    assert r.replacement_cost_inr == 1120 + 340
    assert r.conflict_total_cost_inr == 2499 + 1460


def test_goodwill_over_cap_flagged_but_amount_untouched():
    """E11: policy S5 caps goodwill at Rs 500. We flag; we never adjust."""
    df = _prep([ticket(ticket_id="TK-6", refund_amount_inr="1400",
                       refund_reason_code="GW-OTHER")])
    r = df.iloc[0]
    assert bool(r.flag_goodwill_over_cap)
    assert r.goodwill_excess_inr == 900
    assert r.refund_amount_inr == 1400.0
    assert r.reason_code == "GW-OTHER"


def test_goodwill_within_cap_not_flagged():
    df = _prep([ticket(ticket_id="TK-7", refund_amount_inr="500",
                       refund_reason_code="GW-OTHER")])
    assert not bool(df.iloc[0].flag_goodwill_over_cap)


def test_cap_applies_only_to_goodwill():
    """A Rs 6,999 duplicate-payment refund is a refund, not a goodwill breach."""
    df = _prep([ticket(ticket_id="TK-8", refund_amount_inr="6999",
                       refund_reason_code="DUP-PAYMENT")])
    assert not bool(df.iloc[0].flag_goodwill_over_cap)


def test_open_ticket_refund_is_included_and_flagged():
    """D-10: do not silently delete suspicious records."""
    df = _prep([ticket(ticket_id="TK-9", status="open", resolved_at="",
                       refund_amount_inr="5524", refund_reason_code="RETURN-QC-OK")])
    r = df.iloc[0]
    assert bool(r.flag_ticket_open)
    assert r.refund_amount_inr == 5524.0


def test_refund_exceeding_the_order_value_is_flagged():
    orders = pd.DataFrame([{"order_id": "VR1", "customer_id": "C100000",
                            "sku": "VA-EB-PL1", "order_date": "2025-01-01",
                            "channel": "Amazon", "qty": "1",
                            "order_value_inr": "1000", "lot_code": "L1"}])
    raw = load.load_all()
    t = normalise.normalise(frame([ticket(ticket_id="TK-10", order_id="VR1",
                                          refund_amount_inr="5000",
                                          refund_reason_code="CANCEL")]))
    _, t, _ = dedupe.deduplicate(t)
    t = agents_mod.attach_agents(t, raw["agents"])
    t = joins.attach_orders(t, orders)
    t = joins.attach_products(t, raw["products"])
    t = joins.attach_customers(t, raw["customers"])
    assert bool(policy.apply_policy(t).iloc[0].flag_refund_exceeds_order)


def test_every_flag_writes_readable_evidence():
    df = _prep([ticket(ticket_id="TK-11", refund_amount_inr="1400",
                       refund_reason_code="GW-OTHER", replacement_issued="Y",
                       status="open", resolved_at="")])
    r = df.iloc[0]
    assert r.flag_count >= 3
    for phrase in ("policy S5", "goodwill cap", "open/pending"):
        assert phrase in r.flag_evidence
