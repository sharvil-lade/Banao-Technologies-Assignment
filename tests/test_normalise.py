"""Legacy vs current money, timestamps, reason codes."""
import numpy as np
import pandas as pd
from vireo import normalise, config
from conftest import ticket, frame


def test_legacy_amount_divided_by_100():
    """E5: a legacy-only ticket's paise value becomes rupees, raw value preserved."""
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-1", source_system="legacy_fd",
        refund_amount_inr="699900", refund_reason_code="DUP-PAYMENT")]))
    r = df.iloc[0]
    assert r.refund_amount_inr == 6999.0
    assert r.refund_amount_raw == 699900.0
    assert r.conversion_factor == 100
    assert r.currency_unit_source == "paise"


def test_helpdesk_amount_untouched():
    """E1: a current-helpdesk amount passes through unchanged."""
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-2", source_system="helpdesk",
        refund_amount_inr="3058", refund_reason_code="RETURN-QC-OK")]))
    r = df.iloc[0]
    assert r.refund_amount_inr == 3058.0
    assert r.conversion_factor == 1
    assert r.currency_unit_source == "INR"


def test_conversion_keyed_on_source_not_magnitude():
    """A large genuine rupee refund must not be mistaken for paise."""
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-3", source_system="helpdesk",
        refund_amount_inr="13998", refund_reason_code="GW-OTHER")]))
    assert df.iloc[0].refund_amount_inr == 13998.0


def test_blank_refund_is_not_zero():
    """E2: no refund means absent, never a zero that would drag an average down."""
    df = normalise.normalise(frame([ticket(ticket_id="TK-4")]))
    assert pd.isna(df.iloc[0].refund_amount_inr)
    assert not bool(df.iloc[0].has_refund)


def test_blank_csat_is_nan_not_zero():
    """Policy S8: a blank CSAT is 'no response' and must be excluded from averages."""
    df = normalise.normalise(frame([ticket(ticket_id="TK-5", csat_score=""),
                                    ticket(ticket_id="TK-6", csat_score="4")]))
    assert pd.isna(df.iloc[0].csat)
    assert df.csat.mean() == 4.0


def test_unknown_reason_code_flagged_not_dropped():
    """E12: a code outside policy S5 is kept, labelled UNKNOWN and flagged."""
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-7", refund_amount_inr="500", refund_reason_code="NEW-CODE-2027")]))
    r = df.iloc[0]
    assert len(df) == 1
    assert bool(r.unknown_reason_code)
    assert r.reason_label == "UNKNOWN"
    assert r.refund_amount_inr == 500.0


def test_month_uses_created_at():
    """D-08: month basis is created_at, present on every row."""
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-8", created_at="2025-03-31 23:50", resolved_at="2025-04-02 01:00")]))
    assert df.iloc[0].month == "2025-03"
    assert df.iloc[0].month_resolved == "2025-04"


def test_open_ticket_has_month_but_no_resolved_month():
    df = normalise.normalise(frame([ticket(
        ticket_id="TK-9", status="open", resolved_at="", refund_amount_inr="5524",
        refund_reason_code="RETURN-QC-OK")]))
    r = df.iloc[0]
    assert r.month == "2025-03"
    assert r.month_resolved is None or pd.isna(r.month_resolved)
    assert bool(r.ticket_open)


def test_verify_legacy_conversion_detects_a_changed_unit():
    """If a future export stops using paise, the check must not report 100."""
    rows = [
        ticket(ticket_id="TK-A", source_system="helpdesk", refund_amount_inr="100",
               refund_reason_code="CANCEL"),
        ticket(ticket_id="TK-A", source_system="legacy_fd", refund_amount_inr="1000",
               refund_reason_code="CANCEL"),
    ]
    df = normalise.normalise(frame(rows))
    res = normalise.verify_legacy_conversion(df)
    assert res["factor"] == 10.0
    assert res["factor"] != config.LEGACY_CONVERSION_FACTOR
