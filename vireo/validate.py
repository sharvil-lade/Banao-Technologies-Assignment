"""
Stage 2 - schema validation.

Validation REPORTS problems. It never drops, fixes or hides a row.
Every issue becomes a line in reports/validation.md so a reviewer can see
exactly what the pipeline knew about before it did anything.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import pandas as pd
from . import config


@dataclass
class Issue:
    severity: str   # "error" | "warning" | "info"
    check: str
    detail: str
    count: int
    sample: list = field(default_factory=list)


@dataclass
class ValidationReport:
    issues: list = field(default_factory=list)

    def add(self, severity, check, detail, count, sample=None):
        sample = [] if sample is None else list(sample)
        self.issues.append(Issue(severity, check, detail, int(count), sample[:5]))

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == "error"]

    @property
    def ok(self):
        return not self.errors

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"severity": i.severity, "check": i.check, "detail": i.detail,
                 "count": i.count, "sample": ", ".join(map(str, i.sample))}
                for i in self.issues
            ]
        )


def _enum_check(rep, df, col, allowed, name):
    bad = df[~df[col].isin(allowed)]
    if len(bad):
        rep.add("error", f"{name}.{col}.domain",
                f"values outside {sorted(allowed)}", len(bad),
                bad[col].unique())


def validate_tickets(tickets: pd.DataFrame, rep: ValidationReport | None = None):
    rep = rep or ValidationReport()

    missing = [c for c in config.TICKET_COLUMNS if c not in tickets.columns]
    if missing:
        rep.add("error", "tickets.schema", f"missing columns: {missing}", len(missing))
        return rep
    extra = [c for c in tickets.columns if c not in config.TICKET_COLUMNS]
    if extra:
        rep.add("warning", "tickets.schema", f"unexpected columns: {extra}", len(extra))

    rep.add("info", "tickets.rows", "rows as exported", len(tickets))
    rep.add("info", "tickets.unique_ids", "distinct ticket_id", tickets.ticket_id.nunique())

    _enum_check(rep, tickets, "status", config.STATUS_VALUES, "tickets")
    _enum_check(rep, tickets, "channel", config.CHANNEL_VALUES, "tickets")
    _enum_check(rep, tickets, "priority", config.PRIORITY_VALUES, "tickets")
    _enum_check(rep, tickets, "source_system", config.SOURCE_SYSTEMS, "tickets")
    _enum_check(rep, tickets, "replacement_issued", ("Y", "N"), "tickets")

    # Reason code: blank is legitimate (no refund). Unknown non-blank is not.
    known = set(config.REASON_LABELS) | {""}
    bad = tickets[~tickets.refund_reason_code.isin(known)]
    if len(bad):
        rep.add("error", "tickets.refund_reason_code.domain",
                "unrecognised reason code - row is KEPT and flagged, never dropped",
                len(bad), bad.refund_reason_code.unique())

    # Money must parse.
    amt = pd.to_numeric(tickets.refund_amount_inr.replace("", None), errors="coerce")
    unparsed = tickets[(tickets.refund_amount_inr != "") & amt.isna()]
    if len(unparsed):
        rep.add("error", "tickets.refund_amount_inr.numeric",
                "non-numeric refund amount", len(unparsed),
                unparsed.refund_amount_inr.unique())
    neg = tickets[amt.notna() & (amt < 0)]
    if len(neg):
        rep.add("error", "tickets.refund_amount_inr.sign", "negative refund", len(neg),
                neg.ticket_id)

    # Amount and reason code must travel together.
    a = tickets.refund_amount_inr != ""
    r = tickets.refund_reason_code != ""
    if (a & ~r).any():
        rep.add("warning", "tickets.refund_pairing", "amount present, reason code blank",
                int((a & ~r).sum()), tickets.ticket_id[a & ~r])
    if (r & ~a).any():
        rep.add("warning", "tickets.refund_pairing", "reason code present, amount blank",
                int((r & ~a).sum()), tickets.ticket_id[r & ~a])

    # Timestamps must parse; resolved_at blank only where the ticket is not finished.
    for col in ("created_at", "first_response_at", "resolved_at"):
        ts = pd.to_datetime(tickets[col].replace("", None), errors="coerce")
        bad_ts = tickets[(tickets[col] != "") & ts.isna()]
        if len(bad_ts):
            rep.add("error", f"tickets.{col}.parse", "unparseable timestamp",
                    len(bad_ts), bad_ts.ticket_id)

    blank_res = tickets.resolved_at == ""
    open_like = tickets.status.isin(config.OPEN_STATUSES)
    mism = tickets[blank_res != open_like]
    if len(mism):
        rep.add("warning", "tickets.resolved_at.consistency",
                "blank resolved_at does not match open/pending status",
                len(mism), mism.ticket_id)
    return rep


def validate_references(tickets, agents, orders, customers, products,
                        rep: ValidationReport | None = None):
    """Foreign-key integrity. Orphans are reported, never silently dropped."""
    rep = rep or ValidationReport()
    checks = [
        ("agent_id", tickets.agent_id, set(agents.agent_id), "agents"),
        ("product_sku", tickets.product_sku, set(products.sku), "products"),
        ("customer_id", tickets.customer_id, set(customers.customer_id), "customers"),
        ("order_id", tickets.order_id[tickets.order_id != ""], set(orders.order_id), "orders"),
    ]
    for col, series, valid, target in checks:
        orphans = sorted(set(series) - valid)
        sev = "error" if orphans else "info"
        rep.add(sev, f"fk.{col}->{target}",
                "orphan keys" if orphans else "all keys resolve",
                len(orphans), orphans)
    return rep


def validate_timestamp_ordering(tickets, rep: ValidationReport | None = None):
    """
    Policy S9 warns of a UTC/IST mix. If legacy resolved_at were UTC while
    created_at is IST we would see negative durations. This check is the
    evidence behind decision D-09 and runs on every pipeline execution, so a
    future export that DOES have the shift fails loudly instead of quietly.
    """
    rep = rep or ValidationReport()
    c = pd.to_datetime(tickets.created_at.replace("", None), errors="coerce")
    f = pd.to_datetime(tickets.first_response_at.replace("", None), errors="coerce")
    r = pd.to_datetime(tickets.resolved_at.replace("", None), errors="coerce")
    for name, later, earlier in (("first_response<created", f, c),
                                 ("resolved<created", r, c),
                                 ("resolved<first_response", r, f)):
        bad = (later < earlier).fillna(False)
        rep.add("error" if bad.any() else "info", f"timestamps.{name}",
                "negative duration (possible timezone mix - see D-09)",
                int(bad.sum()), tickets.ticket_id[bad])
    return rep


def validate_all(raw: dict) -> ValidationReport:
    rep = ValidationReport()
    validate_tickets(raw["tickets"], rep)
    validate_references(raw["tickets"], raw["agents"], raw["orders"],
                        raw["customers"], raw["products"], rep)
    validate_timestamp_ordering(raw["tickets"], rep)
    return rep
