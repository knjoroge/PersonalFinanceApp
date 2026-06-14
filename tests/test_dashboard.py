"""Tests for dashboard view helpers (pure-data logic, no Streamlit rendering)."""

import pandas as pd

from views.dashboard import _current_month_rows


def _df(dates):
    """Build a minimal transactions dataframe with datetime dates."""
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "type": ["Expense"] * len(dates),
        "category": ["Food"] * len(dates),
        "amount": [10.0] * len(dates),
    })


def test_current_month_rows_keeps_only_this_month():
    today = pd.Timestamp.today()
    in_month = today.replace(day=1)
    last_month = (in_month - pd.Timedelta(days=1)).replace(day=1)

    df = _df([in_month, today, last_month])
    result = _current_month_rows(df)

    assert len(result) == 2
    assert (result["date"].dt.to_period("M") == today.to_period("M")).all()


def test_current_month_rows_empty_when_no_current_month_data():
    last_month = (pd.Timestamp.today().replace(day=1) - pd.Timedelta(days=1))
    result = _current_month_rows(_df([last_month]))
    assert result.empty


def test_current_month_rows_handles_empty_input():
    empty = pd.DataFrame({"date": pd.to_datetime([]), "type": [], "category": [], "amount": []})
    assert _current_month_rows(empty).empty
