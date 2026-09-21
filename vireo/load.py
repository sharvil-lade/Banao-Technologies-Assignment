"""Stage 1 - loading. Read source files verbatim. No coercion, no cleaning."""
from __future__ import annotations
import pandas as pd
from . import config


def _read(path) -> pd.DataFrame:
    """Read a CSV with every cell as a string and blanks preserved as ''.

    dtype=str + keep_default_na=False means pandas never guesses a type and never
    turns an empty cell into NaN. Type decisions are made later, explicitly, so
    they are visible and testable.
    """
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def load_tickets(path=None) -> pd.DataFrame:
    return _read(path or config.FILES["tickets"])


def load_agents(path=None) -> pd.DataFrame:
    return _read(path or config.FILES["agents"])


def load_orders(path=None) -> pd.DataFrame:
    return _read(path or config.FILES["orders"])


def load_customers(path=None) -> pd.DataFrame:
    return _read(path or config.FILES["customers"])


def load_products(path=None) -> pd.DataFrame:
    return _read(path or config.FILES["products"])


def load_all(raw_dir=None) -> dict:
    """Load every source file. Returns a dict of raw DataFrames."""
    if raw_dir is None:
        paths = config.FILES
    else:
        from pathlib import Path
        raw_dir = Path(raw_dir)
        paths = {k: raw_dir / f"{k}.csv" for k in config.FILES}
    return {name: _read(p) for name, p in paths.items()}
