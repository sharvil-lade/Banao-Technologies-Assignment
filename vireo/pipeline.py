"""
Orchestration: raw -> validated -> normalised -> deduplicated -> joined ->
policy-checked -> canonical -> aggregated -> reconciled.

Run with:  python -m vireo.pipeline
"""
from __future__ import annotations
import sys
import pandas as pd
from . import (config, load, validate, normalise, dedupe, agents as agents_mod,
               joins, policy, canonical, aggregate, reconcile, ai_classify,
               validate_sample, impact, costs)


def run(raw_dir=None, out_dir=None, reports_dir=None, verbose=True,
        ai_backend="two_tier", escalate_backend="cache") -> dict:
    out_dir = config.DERIVED if out_dir is None else __import__("pathlib").Path(out_dir)
    reports_dir = config.REPORTS if reports_dir is None else __import__("pathlib").Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    def say(msg):
        if verbose:
            print(msg, flush=True)

    # 1. load -------------------------------------------------------------
    raw = load.load_all(raw_dir)
    say(f"[1/9] loaded      tickets={len(raw['tickets']):,} agents={len(raw['agents'])} "
        f"orders={len(raw['orders']):,} customers={len(raw['customers']):,} products={len(raw['products'])}")

    # 2. validate ---------------------------------------------------------
    report = validate.validate_all(raw)
    say(f"[2/9] validated   errors={len(report.errors)} issues={len(report.issues)}")
    if not report.ok:
        for i in report.errors:
            say(f"        ERROR {i.check}: {i.detail} ({i.count}) {i.sample}")
        raise SystemExit("validation failed - refusing to build a report on invalid data")

    # 3. normalise --------------------------------------------------------
    norm = normalise.normalise(raw["tickets"])
    conv = normalise.verify_legacy_conversion(norm)
    say(f"[3/9] normalised  legacy factor re-measured from data: {conv['factor']} "
        f"({conv['pairs_observed']} pairs, unanimous={conv['unanimous']})")
    if conv["factor"] is not None and conv["factor"] != config.LEGACY_CONVERSION_FACTOR:
        raise SystemExit(
            f"measured legacy conversion {conv['factor']} != configured "
            f"{config.LEGACY_CONVERSION_FACTOR}. Refusing to run: see D-03.")

    # 4. deduplicate ------------------------------------------------------
    tagged, canon_tickets, dup_audit = dedupe.deduplicate(norm)
    say(f"[4/9] deduplicated pairs={len(dup_audit)} excluded_rows={int((~tagged.is_canonical).sum())} "
        f"canonical_tickets={len(canon_tickets):,}")

    # 5. agents -----------------------------------------------------------
    canon_tickets = agents_mod.attach_agents(canon_tickets, raw["agents"])
    say(f"[5/9] roster      {canon_tickets.roster_match.value_counts().to_dict()}")

    # 6. joins ------------------------------------------------------------
    canon_tickets = joins.attach_all(canon_tickets, raw["orders"], raw["products"], raw["customers"])
    say(f"[6/9] joined      {canon_tickets.order_match.value_counts().to_dict()}")

    # 7. policy -----------------------------------------------------------
    canon_tickets = policy.apply_policy(canon_tickets)
    refunds = canonical.build_canonical_refunds(canon_tickets)
    tickets_tbl = canonical.build_canonical_tickets(canon_tickets)
    say(f"[7/9] policy      refunds={len(refunds):,} total=Rs {refunds.refund_amount_inr.sum():,.0f} "
        f"suspicious={int(refunds.is_suspicious.sum())}")

    # 7b. AI layer --------------------------------------------------------
    # Runs AFTER the canonical table is final. Nothing the model returns can
    # change a refund amount - attach() only adds ai_* columns (D-16).
    total_before = refunds.refund_amount_inr.sum()
    labels = ai_classify.classify(refunds, backend=ai_backend,
                                  escalate_backend=escalate_backend)
    refunds = ai_classify.attach(refunds, labels)
    assert refunds.refund_amount_inr.sum() == total_before, \
        "the AI layer changed a refund total - this must never happen"
    t1 = labels.attrs.get("tier1_count", 0)
    t2 = labels.attrs.get("tier2_count", 0)
    say(f"[7b/9] ai         tier1(rules,free)={t1:,} tier2(model)={t2:,} "
        f"({t2 / max(len(refunds), 1) * 100:.1f}% escalated) "
        f"reason_mismatch={int(refunds.flag_reason_mismatch.sum()):,}")

    # 8. aggregate --------------------------------------------------------
    monthly = aggregate.monthly_summary(refunds, tickets_tbl)
    reason = aggregate.by_reason(refunds)
    reason_month = aggregate.by_reason_month(refunds)
    agent = aggregate.by_agent(refunds, tickets_tbl)
    team = aggregate.by_team(refunds, tickets_tbl)
    suspicious = aggregate.suspicious_cases(refunds)
    reason_restated = aggregate.by_reason_restated(refunds)
    goodwill_check = aggregate.goodwill_reality_check(refunds)
    theme = aggregate.by_theme(refunds)
    ai_cov = aggregate.ai_coverage(refunds)
    say(f"[8/9] aggregated  months={len(monthly)} reasons={len(reason)} agents={len(agent)}")

    # 9. reconcile --------------------------------------------------------
    bridge = reconcile.build_bridge(tagged, refunds)
    residual = reconcile.bridge_residual(bridge)
    identities = reconcile.aggregation_identities(refunds, monthly, reason, agent)
    comparison = reconcile.client_number_comparison(refunds)
    say(f"[9/9] reconciled  residual=Rs {residual:.2f} "
        f"identities={'ALL PASS' if (identities.result == 'PASS').all() else 'FAILED'}")

    if abs(residual) > 0.01:
        raise SystemExit(f"reconciliation residual Rs {residual} - refusing to publish")
    if not (identities.result == "PASS").all():
        raise SystemExit("aggregation identity failed - refusing to publish")

    # 10. independent verification + business impact -----------------------
    sample_df, sample_summary = validate_sample.verify_sample(refunds, n=60)
    indep = validate_sample.verify_totals_independently(refunds)
    buckets = impact.build_buckets(refunds)
    impact_summary = impact.summarise(refunds, buckets)
    cost_run = costs.measure_run(refunds, labels)
    cost_month = costs.project_monthly(cost_run, 650, refunds=refunds, tickets=tickets_tbl)
    say(f"[10/10] verified   sample={sample_summary['sample_size']} rows, "
        f"{sample_summary['field_checks_run']} field checks, "
        f"error rate {sample_summary['field_error_rate_pct']}% | "
        f"independent total {'PASS' if (indep.result != 'FAIL').all() else 'FAIL'} | "
        f"avoidable Rs {impact_summary['avoidable_identified_per_quarter_inr']:,}/qtr")
    if (indep.result == "FAIL").any():
        raise SystemExit("independent recomputation disagrees with the pipeline")
    if sample_summary["field_checks_failed"] > 0:
        say(f"        WARNING: {sample_summary['field_checks_failed']} field checks failed "
            f"- see sample_verification.csv")

    outputs = {
        "canonical_refunds": refunds,
        "canonical_tickets": tickets_tbl,
        "duplicate_audit": dup_audit,
        "monthly_summary": monthly,
        "by_reason": reason,
        "by_reason_month": reason_month,
        "by_agent": agent,
        "by_team": team,
        "suspicious_cases": suspicious,
        "reconciliation_bridge": bridge,
        "reconciliation_identities": identities,
        "client_number_comparison": comparison,
        "validation_report": report.to_frame(),
        "by_reason_restated": reason_restated,
        "goodwill_reality_check": goodwill_check,
        "by_theme": theme,
        "ai_coverage": ai_cov,
        "ai_labels": labels,
        "sample_verification": sample_df,
        "independent_recomputation": indep,
        "business_impact": buckets,
        "business_impact_summary": pd.DataFrame([impact_summary]),
        "cost_per_run": pd.DataFrame([cost_run]),
        "cost_monthly": pd.DataFrame([cost_month]),
    }
    for name, df in outputs.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    _write_reconciliation_md(reports_dir / "reconciliation.md", bridge, identities,
                             comparison, dup_audit, conv, monthly)
    _write_validation_md(reports_dir / "validation.md", report.to_frame())
    say(f"      wrote {len(outputs)} tables to {out_dir} and 2 reports to {reports_dir}")
    return outputs


def _inr(x):
    return f"Rs {x:,.0f}"


def _write_reconciliation_md(path, bridge, identities, comparison, dup_audit, conv, monthly):
    L = []
    L.append("# Reconciliation Report\n")
    L.append("_Generated by `python -m vireo.pipeline`. Every figure below is computed "
             "from `data/raw/`; nothing is typed in by hand._\n")
    L.append("## 1. The bridge: raw export to canonical total\n")
    L.append("| Step | Adjustment | Running total | Rows | Why |")
    L.append("|---|---:|---:|---:|---|")
    for _, r in bridge.iterrows():
        adj = "" if pd.isna(r.adjustment_inr) else _inr(r.adjustment_inr)
        L.append(f"| {r.step} | {adj} | **{_inr(r.running_total_inr)}** | {r.rows_affected:,} | {r.why} |")
    residual = bridge.iloc[2].running_total_inr - bridge.iloc[3].running_total_inr
    L.append(f"\n**Residual: {_inr(residual)}** - the bridge closes exactly.\n")

    L.append("## 2. Against the two client numbers\n")
    L.append("| Source | Claim | Reproducible from the data? | Per quarter |")
    L.append("|---|---|---|---:|")
    for _, r in comparison.iterrows():
        pq = "" if r.per_quarter_inr is None or pd.isna(r.per_quarter_inr) else _inr(r.per_quarter_inr)
        L.append(f"| {r.source} | {r.claim} | {r.reproducible_from_data} | {pq} |")

    L.append("\n## 3. Legacy conversion, re-measured on this run\n")
    L.append(f"- Duplicate pairs carrying an amount on both sides: **{conv['pairs_observed']}**")
    L.append(f"- Observed legacy/helpdesk ratio: **{conv['factor']}**, unanimous: **{conv['unanimous']}**, "
             f"std dev **{conv['ratio_std']}**")
    L.append(f"- Legacy amounts divisible by 100: **{conv['legacy_divisible_by_100_pct']:.1f}%**")
    L.append("\nThe factor is not hard-coded trust: the pipeline re-derives it from the data on "
             "every run and aborts if it stops matching.\n")
    ok = int((dup_audit.amounts_reconcile == "yes").sum())
    bad = int((dup_audit.amounts_reconcile == "no").sum())
    L.append(f"After conversion, **{ok} of {ok + bad}** duplicate pairs with money agree to the "
             f"rupee across both systems ({bad} disagree). This is an independent confirmation "
             "that the factor is right.\n")

    L.append("## 4. Aggregation identities\n")
    L.append("| Identity | Computed | Expected | Difference | Result |")
    L.append("|---|---:|---:|---:|---|")
    for _, r in identities.iterrows():
        L.append(f"| {r.identity} | {r.computed:,.2f} | {r.expected:,.2f} | {r.difference:,.2f} | **{r.result}** |")

    L.append("\n## 5. Monthly canonical refunds\n")
    L.append("| Month | Refund value | Refunds | Tickets | Refund rate | Suspicious | Replacement conflicts |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for _, r in monthly.iterrows():
        L.append(f"| {r.month} | {_inr(r.refund_amount_inr)} | {int(r.refund_count)} | "
                 f"{int(r.tickets_total)} | {r.refund_rate_pct}% | {int(r.suspicious_count)} | "
                 f"{int(r.replacement_conflicts)} |")
    total = monthly.refund_amount_inr.sum()
    L.append(f"| **Total** | **{_inr(total)}** | **{int(monthly.refund_count.sum())}** | "
             f"**{int(monthly.tickets_total.sum())}** | | | |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def _write_validation_md(path, frame):
    L = ["# Validation Report\n",
         "_Schema, domain, foreign-key and timestamp checks run on every pipeline execution._\n",
         "Validation reports problems; it never drops, fixes or hides a row.\n",
         "| Severity | Check | Detail | Count | Sample |", "|---|---|---|---:|---|"]
    for _, r in frame.iterrows():
        L.append(f"| {r.severity} | `{r.check}` | {r.detail} | {r['count']:,} | {r['sample']} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
