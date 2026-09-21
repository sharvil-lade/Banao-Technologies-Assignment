"""
Stage 6 - order / customer / product joins.

Everything here is CONTEXT. No reported money figure depends on any of it, which
is what makes D-06 (leave ambiguous joins unresolved) safe: an unresolved join
costs a reviewer some context and costs the totals nothing.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def attach_orders(tickets: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """
    Direct join on order_id; documented fallback on customer_id + product_sku.

    D-06: where the fallback finds more than one candidate order we attach
    NOTHING and record the candidate count. Picking "the most recent order"
    would be a rule we invented, and inventing rules is how a reconciliation
    stops being a reconciliation.
    """
    o = orders.copy()
    o["order_value_inr_n"] = pd.to_numeric(o.order_value_inr, errors="coerce")
    o["order_qty"] = pd.to_numeric(o.qty, errors="coerce")
    n_before = len(tickets)

    direct = o.set_index("order_id")
    out = tickets.copy()
    has_id = out.order_id != ""
    for src, dst in (("order_value_inr_n", "order_value_inr"), ("order_qty", "order_qty"),
                     ("channel", "order_channel"), ("lot_code", "lot_code"),
                     ("order_date", "order_date")):
        out[dst] = out.order_id.where(has_id).map(direct[src])
    out["order_match"] = np.where(has_id, "direct", "none")
    out["order_candidates"] = np.where(has_id, 1, 0)

    # Fallback for tickets with no quoted order_id.
    cand = (o.groupby(["customer_id", "sku"])
              .agg(n=("order_id", "size"), order_id=("order_id", "first"),
                   order_value_inr_n=("order_value_inr_n", "first"),
                   order_qty=("order_qty", "first"), channel=("channel", "first"),
                   lot_code=("lot_code", "first"), order_date=("order_date", "first")))

    need = ~has_id
    key = pd.MultiIndex.from_arrays([out.loc[need, "customer_id"],
                                     out.loc[need, "product_sku"]])
    sub = cand.reindex(key)
    sub.index = out.index[need]

    out.loc[need, "order_candidates"] = sub.n.fillna(0).astype(int)
    unique = need & (out.order_candidates == 1)
    ambiguous = need & (out.order_candidates > 1)

    out.loc[unique, "order_id"] = sub.loc[unique[unique].index, "order_id"]
    out.loc[unique, "order_value_inr"] = sub.loc[unique[unique].index, "order_value_inr_n"]
    out.loc[unique, "order_qty"] = sub.loc[unique[unique].index, "order_qty"]
    out.loc[unique, "order_channel"] = sub.loc[unique[unique].index, "channel"]
    out.loc[unique, "lot_code"] = sub.loc[unique[unique].index, "lot_code"]
    out.loc[unique, "order_date"] = sub.loc[unique[unique].index, "order_date"]

    out.loc[unique, "order_match"] = "fallback_unique"
    out.loc[ambiguous, "order_match"] = "ambiguous"          # nothing attached, by design
    out.loc[need & (out.order_candidates == 0), "order_match"] = "no_match"

    assert len(out) == n_before, "order join changed the row count"
    return out


def attach_products(tickets: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    p = products.copy()
    p["unit_cost_inr_n"] = pd.to_numeric(p.unit_cost_inr, errors="coerce")
    p["retail_price_inr_n"] = pd.to_numeric(p.retail_price_inr, errors="coerce")
    m = p.set_index("sku")
    out = tickets.copy()
    out["product_name"] = out.product_sku.map(m.product_name)
    out["product_family"] = out.product_sku.map(m.family)
    out["unit_cost_inr"] = out.product_sku.map(m.unit_cost_inr_n)
    out["retail_price_inr"] = out.product_sku.map(m.retail_price_inr_n)
    return out


def attach_customers(tickets: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    m = customers.set_index("customer_id")
    out = tickets.copy()
    out["customer_city"] = out.customer_id.map(m.city)
    out["customer_state"] = out.customer_id.map(m.state)
    out["care_plus"] = out.customer_id.map(m.care_plus)
    return out


def attach_all(tickets, orders, products, customers) -> pd.DataFrame:
    df = attach_orders(tickets, orders)
    df = attach_products(df, products)
    df = attach_customers(df, customers)
    return df
