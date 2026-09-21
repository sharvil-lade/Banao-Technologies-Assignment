"""
Regression tests against the supplied data pack.

These lock in figures the pipeline computed, so a future change that moves a
number has to be deliberate. They are regression guards, not independent truth:
the evidence for each figure lives in docs/data-audit.md and reports/reconciliation.md.

The named tickets are the behavioural contract in docs/data-dictionary.md Part 3.
"""
import pandas as pd
import pytest

CANONICAL_TICKETS = 11_600
CANONICAL_REFUNDS = 2_340
CANONICAL_TOTAL_INR = 6_709_932.0
RAW_EXPORT_TOTAL_INR = 230_124_081.0
DUPLICATE_PAIRS = 638


def test_row_counts(real_refunds):
    assert len(real_refunds["canonical_tickets"]) == CANONICAL_TICKETS
    assert len(real_refunds["canonical_refunds"]) == CANONICAL_REFUNDS
    assert len(real_refunds["duplicate_audit"]) == DUPLICATE_PAIRS


def test_canonical_total(real_refunds):
    assert real_refunds["canonical_refunds"].refund_amount_inr.sum() == CANONICAL_TOTAL_INR


def test_ticket_id_is_unique_in_every_published_table(real_refunds):
    assert real_refunds["canonical_refunds"].ticket_id.is_unique
    assert real_refunds["canonical_tickets"].ticket_id.is_unique


def test_reconciliation_bridge_closes(real_refunds):
    from vireo import reconcile
    b = real_refunds["reconciliation_bridge"]
    assert b.iloc[0].running_total_inr == RAW_EXPORT_TOTAL_INR
    assert b.iloc[3].running_total_inr == CANONICAL_TOTAL_INR
    assert reconcile.bridge_residual(b) == 0.0


def test_all_aggregation_identities_pass(real_refunds):
    assert (real_refunds["reconciliation_identities"].result == "PASS").all()


def test_the_crore_is_reproducible_and_the_lakh_is_the_truth(real_refunds):
    """
    The heart of the engagement. Arjun's 'well over a crore a quarter' is what
    the raw export gives; Sameer's 'around Rs 11 lakh a quarter' is what the
    data actually supports.
    """
    raw_per_quarter = RAW_EXPORT_TOTAL_INR / 6
    assert raw_per_quarter > 1_00_00_000            # over a crore, as Finance reports
    per_quarter = (real_refunds["canonical_refunds"]
                   .groupby("quarter").refund_amount_inr.sum().mean())
    assert 10_00_000 < per_quarter < 12_00_000      # around 11 lakh, as the helpdesk reports


# ---- named tickets from the behavioural contract (data-dictionary.md Part 3) ----

def test_E1_normal_helpdesk_refund(real_refunds):
    r = real_refunds["canonical_refunds"].set_index("ticket_id").loc["TK-246239"]
    assert r.refund_amount_inr == 3058.0
    assert r.conversion_factor == 1
    assert r.duplicate_status == "unique"
    assert r.month == "2025-10"


def test_E2_ticket_without_a_refund_is_absent_from_the_refund_table(real_refunds):
    assert "TK-246244" not in set(real_refunds["canonical_refunds"].ticket_id)
    assert "TK-246244" in set(real_refunds["canonical_tickets"].ticket_id)


def test_E3_duplicate_pair_resolves_to_the_rupee_value(real_refunds):
    r = real_refunds["canonical_refunds"].set_index("ticket_id").loc["TK-240003"]
    assert r.refund_amount_inr == 900.0
    assert r.record_role == "canonical_of_pair"
    assert r.source_system == "helpdesk"
    a = real_refunds["duplicate_audit"].set_index("ticket_id").loc["TK-240003"]
    assert a.excluded_amount_raw == 90000.0
    assert a.observed_ratio == 100.0


def test_E5_legacy_only_ticket_converted(real_refunds):
    r = real_refunds["canonical_refunds"].set_index("ticket_id").loc["TK-240031"]
    assert r.refund_amount_inr == 6999.0
    assert r.refund_amount_raw == 699900.0
    assert r.currency_unit_source == "paise"


def test_E6_open_ticket_refund_is_present_and_flagged(real_refunds):
    r = real_refunds["canonical_refunds"].set_index("ticket_id").loc["TK-246285"]
    assert r.refund_amount_inr == 5524.0
    assert bool(r.flag_ticket_open)


def test_E8_ambiguous_fallback_attaches_no_order(real_refunds):
    amb = real_refunds["canonical_refunds"].query("order_match == 'ambiguous'")
    assert len(amb) > 0
    assert amb.order_value_inr.isna().all()
    assert (amb.order_id == "").all()


def test_no_paise_value_survives_anywhere(real_refunds):
    """
    The single most damaging possible bug: a legacy amount banked as rupees.
    The largest legitimate refund is Rs 13,998 (a multi-unit order), so anything
    above Rs 50,000 in the canonical table would be an unconverted paise value.
    """
    assert real_refunds["canonical_refunds"].refund_amount_inr.max() < 50_000


def test_every_refund_is_positive_and_present(real_refunds):
    a = real_refunds["canonical_refunds"].refund_amount_inr
    assert a.notna().all() and (a > 0).all()


def test_every_flag_carries_evidence(real_refunds):
    r = real_refunds["canonical_refunds"]
    flagged = r[r.flag_count > 0]
    assert len(flagged) > 0
    assert (flagged.flag_evidence.str.len() > 0).all()


def test_suspicious_cases_all_trace_to_a_real_ticket(real_refunds):
    s = real_refunds["suspicious_cases"]
    assert set(s.ticket_id).issubset(set(real_refunds["canonical_refunds"].ticket_id))
    assert (s.flag_evidence.str.len() > 0).all()


def test_replacement_conflicts_exceed_the_structured_flag_alone(real_refunds):
    """
    Neha Kulkarni called these 'probably one-offs'. Both detectors together find
    materially more than replacement_issued=Y alone.
    """
    r = real_refunds["canonical_refunds"]
    assert int(r.flag_refund_and_replacement.sum()) == 166
    assert int(r.flag_replacement_conflict_any.sum()) > 166


def test_goodwill_cap_breaches_are_the_dominant_policy_exception(real_refunds):
    r = real_refunds["canonical_refunds"]
    gw = r[r.reason_code == "GW-OTHER"]
    assert int(gw.flag_goodwill_over_cap.sum()) == 879
    assert gw.refund_amount_inr.sum() / r.refund_amount_inr.sum() > 0.40
