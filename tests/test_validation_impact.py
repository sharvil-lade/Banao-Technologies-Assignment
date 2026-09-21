"""Independent verification and the business-impact model."""
import numpy as np
import pandas as pd
import pytest
from vireo import validate_sample, impact, costs, config


def test_independent_recomputation_agrees(real_refunds):
    """A second implementation, stdlib only, must reach the same total."""
    out = validate_sample.verify_totals_independently(real_refunds["canonical_refunds"])
    assert (out[out.result != "INFO"].result == "PASS").all()


def test_sample_verification_is_clean(real_refunds):
    df, s = validate_sample.verify_sample(real_refunds["canonical_refunds"], n=60)
    assert s["sample_size"] == 60
    assert s["checks_per_row"] == 15
    assert s["field_checks_failed"] == 0, s["failures_by_check"]
    assert s["row_error_rate_pct"] == 0.0


def test_sample_is_reproducible(real_refunds):
    """Same seed, same sample - so a reported error rate can be re-checked."""
    a, _ = validate_sample.verify_sample(real_refunds["canonical_refunds"], n=30, seed=7)
    b, _ = validate_sample.verify_sample(real_refunds["canonical_refunds"], n=30, seed=7)
    assert list(a.ticket_id) == list(b.ticket_id)


def test_impact_buckets_do_not_double_count(real_refunds):
    """A ticket may appear in at most one bucket - the whole point of the design."""
    r = real_refunds["canonical_refunds"]
    b = impact.build_buckets(r)
    assert b.tickets.sum() == b.attrs["tickets_claimed"]


def test_impact_never_claims_more_than_the_refunds_exist(real_refunds):
    r = real_refunds["canonical_refunds"]
    b = impact.build_buckets(r)
    s = impact.summarise(r, b)
    assert s["avoidable_identified_per_quarter_inr"] < s["baseline_refunds_per_quarter_inr"]
    assert s["target_saving_per_quarter_inr"] <= s["avoidable_identified_per_quarter_inr"]


def test_duplicate_remedy_bucket_is_conservative():
    """
    Only the CHEAPER remedy is counted as waste. If the refund is 5,000 and the
    replacement costs 1,460, the claim is 1,460 - not 6,460.
    """
    r = pd.DataFrame([{
        "ticket_id": "TK-1", "refund_amount_inr": 5000.0, "unit_cost_inr": 1120.0,
        "flag_replacement_conflict_any": True, "ai_theme": "hardware_fault",
        "ai_suggested_reason": "WTY-BUYBACK", "agent_notes": "", "channel": "chat",
        "transfers_n": 0,
    }])
    b = impact.build_buckets(r)
    assert b.iloc[0].observed_total_inr == 1120 + config.REPLACEMENT_LOGISTICS_INR


def test_payment_failure_bucket_counts_handling_not_the_refund():
    """The refund reverses money wrongly collected; it is not a loss."""
    r = pd.DataFrame([{
        "ticket_id": "TK-2", "refund_amount_inr": 9999.0, "unit_cost_inr": 500.0,
        "flag_replacement_conflict_any": False, "ai_theme": "payment_failure",
        "ai_suggested_reason": "DUP-PAYMENT", "agent_notes": "", "channel": "chat",
        "transfers_n": 0,
    }])
    b = impact.build_buckets(r)
    assert b.iloc[0].observed_total_inr == config.CONTACT_COST_INR["chat"]
    assert b.iloc[0].observed_total_inr < 9999


def test_goodwill_bucket_counts_only_the_excess_over_the_cap():
    r = pd.DataFrame([{
        "ticket_id": "TK-3", "refund_amount_inr": 1500.0, "unit_cost_inr": 500.0,
        "flag_replacement_conflict_any": False, "ai_theme": "service_recovery",
        "ai_suggested_reason": "GW-OTHER", "agent_notes": "", "channel": "chat",
        "transfers_n": 0,
    }])
    b = impact.build_buckets(r)
    assert b.iloc[0].observed_total_inr == 1500 - config.GOODWILL_CAP_INR


def test_cost_model_scales_with_escalations_only(real_refunds):
    r = real_refunds["canonical_refunds"]
    run = costs.measure_run(r, real_refunds["ai_labels"])
    assert run["tier2_model_calls"] + run["tier1_free"] == len(r)
    assert run["escalation_rate_pct"] < 10
    proj = costs.project_monthly(run, 650, refunds=r, tickets=real_refunds["canonical_tickets"])
    assert proj["monthly_inr_claude-sonnet-4-5"] < proj["naive_all_to_model_monthly_inr"]
    assert proj["saving_vs_naive_pct"] > 80


def test_ai_layer_cannot_change_a_refund_total(real_refunds):
    """The single most important invariant in the system."""
    from vireo import ai_classify
    r = real_refunds["canonical_refunds"]
    before = r.refund_amount_inr.sum()
    again = ai_classify.attach(r.drop(columns=[c for c in ai_classify.AI_COLUMNS if c in r]),
                               real_refunds["ai_labels"])
    assert again.refund_amount_inr.sum() == before


def test_rules_tier_accuracy_against_the_gold_set(real_refunds):
    """Locks in the measured accuracy so a pattern edit cannot quietly regress it."""
    from vireo import ai_classify
    gold = pd.read_csv(config.ROOT / "data" / "eval" / "gold_labels.csv")
    r = real_refunds["canonical_refunds"]
    lab = ai_classify.classify_rules(r[r.ticket_id.isin(gold.ticket_id)])
    m = gold.merge(lab, on="ticket_id")
    resolved = m[m.ai_suggested_reason != "INSUFFICIENT-EVIDENCE"]
    acc = (resolved.gold_reason == resolved.ai_suggested_reason).mean()
    assert len(m) == 168
    assert acc >= 0.95, f"tier-1 accuracy regressed to {acc:.3f}"
