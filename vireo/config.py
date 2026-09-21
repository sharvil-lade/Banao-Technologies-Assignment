"""
Constants. Every value here is traceable to a named source in the data pack.
Nothing here is a guess; anything uncertain carries a decision reference
into docs/decisions.md.
"""
from pathlib import Path

PIPELINE_VERSION = "1.0.0"

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
REPORTS = ROOT / "reports"

FILES = {
    "tickets": RAW / "tickets.csv",
    "agents": RAW / "agents.csv",
    "orders": RAW / "orders.csv",
    "customers": RAW / "customers.csv",
    "products": RAW / "products.csv",
}

# ------------------------------------------------- support-policy.pdf v3.2 S5
REASON_LABELS = {
    "GW-OTHER": "Goodwill / Other",
    "DOA-REPL": "Dead on arrival, refund chosen",
    "LOST-TRANSIT": "Lost or undelivered",
    "DUP-PAYMENT": "Duplicate or failed payment",
    "CANCEL": "Cancellation before dispatch",
    "PRICE-ADJ": "Price or coupon adjustment",
    "RETURN-QC-OK": "Return received and passed QC",
    "WTY-BUYBACK": "Warranty buy-back",
}
# "the first option in the list is GW-OTHER" - Sameer Qureshi, 7 Sep
DROPDOWN_DEFAULT_REASON = "GW-OTHER"

GOODWILL_CAP_INR = 500           # S5 "Goodwill credits are capped at Rs 500 per ticket"
REPLACEMENT_LOGISTICS_INR = 340  # S5 "plus Rs 340 for reverse pickup and forward shipping"

# ------------------------------------------------- support-policy.pdf v3.2 S4
CONTACT_COST_INR = {"chat": 210, "email": 260, "voice": 520, "social": 240}
BLENDED_CONTACT_COST_INR = 290
TRANSFER_COST_INR = 305
AGENT_HOUR_COST_INR = 165

# ------------------------------------------------- support-policy.pdf v3.2 S3
FIRST_RESPONSE_TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
SLA_BREACH_CREDIT_INR = 350

# ------------------------------------------------- support-policy.pdf v3.2 S9
HELPDESK_GOLIVE = "2025-09-14"
# D-03: legacy_fd stores paise. Measured from 125 duplicate pairs, ratio 100.0,
# zero variance. Not an assumption - see docs/decisions.md.
LEGACY_CONVERSION_FACTOR = 100
SOURCE_SYSTEMS = ("helpdesk", "legacy_fd")
# D-02: the current helpdesk is the system of record for a duplicate pair.
SOURCE_PRIORITY = {"helpdesk": 0, "legacy_fd": 1}

# ------------------------------------------------- support-policy.pdf v3.2 S6
TIER2_TEAMS = ("Escalations & Warranty",)
REFUND_OWNING_TEAMS = ("Returns Desk",)

STATUS_VALUES = ("resolved", "closed", "open", "pending")
CHANNEL_VALUES = ("chat", "email", "voice", "social")
PRIORITY_VALUES = ("Low", "Normal", "High")
OPEN_STATUSES = ("open", "pending")

TICKET_COLUMNS = [
    "ticket_id", "created_at", "first_response_at", "resolved_at", "status",
    "channel", "customer_id", "order_id", "product_sku", "category", "priority",
    "assigned_team", "agent_id", "transfers", "csat_score", "refund_amount_inr",
    "refund_reason_code", "replacement_issued", "customer_message", "agent_notes",
    "source_system",
]

# Business columns that must match for two rows to be a confident migration duplicate.
# Deliberately excludes refund_amount_inr (units differ) and source_system.
DUPLICATE_MATCH_COLUMNS = [
    "created_at", "first_response_at", "resolved_at", "status", "channel",
    "customer_id", "order_id", "product_sku", "category", "priority",
    "assigned_team", "agent_id", "transfers", "csat_score",
    "refund_reason_code", "replacement_issued", "customer_message", "agent_notes",
]
