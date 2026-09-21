"""Duplicate detection, canonical choice, and the audit trail."""
import pandas as pd
from vireo import normalise, dedupe
from conftest import ticket, frame


def _pair(**over):
    base = dict(over)
    return [ticket(source_system="helpdesk", **base),
            ticket(source_system="legacy_fd", **base)]


def test_exact_pair_keeps_helpdesk_row():
    """E3: helpdesk 900 + legacy 90000 collapses to one row worth Rs 900."""
    rows = _pair(ticket_id="TK-240003", refund_amount_inr="900",
                 refund_reason_code="GW-OTHER")
    rows[1]["refund_amount_inr"] = "90000"
    tagged, canon, audit = dedupe.deduplicate(normalise.normalise(frame(rows)))
    assert len(canon) == 1
    assert canon.iloc[0].source_system == "helpdesk"
    assert canon.iloc[0].refund_amount_inr == 900.0
    assert canon.iloc[0].record_role == "canonical_of_pair"


def test_paise_value_never_reaches_output():
    """Regression guard: Rs 90,000 must not appear anywhere in the canonical data."""
    rows = _pair(ticket_id="TK-240003", refund_amount_inr="900",
                 refund_reason_code="GW-OTHER")
    rows[1]["refund_amount_inr"] = "90000"
    _, canon, _ = dedupe.deduplicate(normalise.normalise(frame(rows)))
    assert 90000.0 not in set(canon.refund_amount_inr.dropna())


def test_excluded_twin_is_retained_in_the_audit_not_deleted():
    rows = _pair(ticket_id="TK-240003", refund_amount_inr="900",
                 refund_reason_code="GW-OTHER")
    rows[1]["refund_amount_inr"] = "90000"
    _, _, audit = dedupe.deduplicate(normalise.normalise(frame(rows)))
    a = audit.iloc[0]
    assert a.excluded_source_system == "legacy_fd"
    assert a.excluded_amount_raw == 90000.0
    assert a.observed_ratio == 100.0
    assert a.amounts_reconcile == "yes"
    assert a.duplicate_confidence == "high"


def test_pair_with_no_money_still_deduplicates():
    """E4: a duplicate with no refund must be counted once, not twice."""
    rows = _pair(ticket_id="TK-240002")
    _, canon, audit = dedupe.deduplicate(normalise.normalise(frame(rows)))
    assert len(canon) == 1
    assert audit.iloc[0].amounts_reconcile == "both blank"


def test_unique_ticket_untouched():
    _, canon, audit = dedupe.deduplicate(
        normalise.normalise(frame([ticket(ticket_id="TK-777")])))
    assert len(canon) == 1
    assert canon.iloc[0].duplicate_status == "unique"
    assert audit.empty


def test_conflicting_pair_keeps_both_rows_and_flags_them():
    """
    A repeated ticket_id whose business columns disagree is NOT a migration
    duplicate. The pipeline must not guess: both rows survive, flagged.
    """
    rows = _pair(ticket_id="TK-888", refund_amount_inr="100",
                 refund_reason_code="CANCEL")
    rows[1]["agent_id"] = "A3001"          # a real disagreement
    tagged, canon, audit = dedupe.deduplicate(normalise.normalise(frame(rows)))
    assert len(canon) == 2
    assert (tagged.duplicate_status == "conflicting_pair").all()
    assert audit.iloc[0].duplicate_confidence == "low"


def test_same_ticket_twice_in_one_system_is_not_a_migration_pair():
    rows = [ticket(ticket_id="TK-999", source_system="helpdesk"),
            ticket(ticket_id="TK-999", source_system="helpdesk")]
    tagged, canon, _ = dedupe.deduplicate(normalise.normalise(frame(rows)))
    assert (tagged.duplicate_status == "conflicting_pair").all()
    assert len(canon) == 2


def test_naive_drop_duplicates_would_have_been_wrong():
    """
    Documents why this module exists. pandas.drop_duplicates() on the full row
    keeps both rows (they differ on amount and source), and on ticket_id alone
    keeps whichever came first - here the paise one.
    """
    rows = _pair(ticket_id="TK-240003", refund_amount_inr="900",
                 refund_reason_code="GW-OTHER")
    rows[1]["refund_amount_inr"] = "90000"
    raw = frame(rows).iloc[::-1]                      # legacy row first
    naive = raw.drop_duplicates("ticket_id", keep="first")
    assert naive.iloc[0].refund_amount_inr == "90000"  # the bug we avoid

    _, canon, _ = dedupe.deduplicate(normalise.normalise(raw))
    assert canon.iloc[0].refund_amount_inr == 900.0    # what we actually produce
