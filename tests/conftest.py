import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vireo import load, normalise, dedupe, agents as agents_mod, joins, policy, canonical  # noqa: E402

BASE = {
    "ticket_id": "TK-900001", "created_at": "2025-03-04 10:00",
    "first_response_at": "2025-03-04 10:05", "resolved_at": "2025-03-04 12:00",
    "status": "resolved", "channel": "chat", "customer_id": "C100000",
    "order_id": "", "product_sku": "VA-EB-PL1", "category": "Returns & Refunds",
    "priority": "Normal", "assigned_team": "Returns Desk", "agent_id": "A3036",
    "transfers": "0", "csat_score": "", "refund_amount_inr": "",
    "refund_reason_code": "", "replacement_issued": "N",
    "customer_message": "hello", "agent_notes": "note", "source_system": "helpdesk",
}


def ticket(**over):
    row = dict(BASE)
    row.update(over)
    return row


def frame(rows):
    return pd.DataFrame(rows).astype(str)


@pytest.fixture(scope="session")
def real_refunds():
    """The canonical refund table built from the supplied data pack."""
    from vireo import pipeline
    return pipeline.run(verbose=False)


@pytest.fixture
def make_canonical():
    """Build the canonical refund table from a synthetic ticket frame."""
    def _build(rows, agents_df=None, orders_df=None,
               products_df=None, customers_df=None):
        raw = load.load_all()
        agents_df = raw["agents"] if agents_df is None else agents_df
        orders_df = raw["orders"] if orders_df is None else orders_df
        products_df = raw["products"] if products_df is None else products_df
        customers_df = raw["customers"] if customers_df is None else customers_df

        t = normalise.normalise(frame(rows))
        _, canon, audit = dedupe.deduplicate(t)
        canon = agents_mod.attach_agents(canon, agents_df)
        canon = joins.attach_all(canon, orders_df, products_df, customers_df)
        canon = policy.apply_policy(canon)
        return canonical.build_canonical_refunds(canon), canon, audit
    return _build
