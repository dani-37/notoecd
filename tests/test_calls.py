import pandas as pd
from types import SimpleNamespace
from unittest.mock import patch
import notoecd.calls as calls


def _fake_structure_with_toc_titles(titles):
    toc = pd.DataFrame({"title": titles})
    return SimpleNamespace(toc=toc)


def test_build_filter_expression_orders_by_toc_and_uppercases():
    fake_s = _fake_structure_with_toc_titles(["PRICES", "UNIT_MEASURE", "MEASURE"])
    filters = {"prices": "q", "unit_measure": ["USD_PPP_PS"], "measure": "gdp"}

    with patch("notoecd.calls.get_structure", return_value=fake_s):
        expr = calls._build_filter_expression("A", "B", filters)

    assert expr == "Q.USD_PPP_PS.GDP"


def test_build_filter_expression_missing_dims_are_empty_parts():
    fake_s = _fake_structure_with_toc_titles(["A", "B", "C"])

    with patch("notoecd.calls.get_structure", return_value=fake_s):
        expr = calls._build_filter_expression("A", "B", {"b": "x"})

    assert expr == ".X."


def test_build_filter_expression_multi_value_joins_plus():
    fake_s = _fake_structure_with_toc_titles(["territorial_level"])

    with patch("notoecd.calls.get_structure", return_value=fake_s):
        expr = calls._build_filter_expression("A", "B", {"territorial_level": ["tl2", "tl3"]})

    assert expr == "TL2+TL3"


def test_get_df_builds_url_and_returns_copy():
    calls._fetch_df.cache_clear()

    fake_s = _fake_structure_with_toc_titles(["PRICES"])
    fake_df = pd.DataFrame({"x": [1, 2]})

    with patch("notoecd.calls.get_structure", return_value=fake_s), \
         patch("notoecd.calls.pd.read_csv", return_value=fake_df) as mock_read_csv:
        out = calls.get_df("OECD.CFE.EDS", "DSD_REG_ECO@DF_GDP", {"prices": "q"})

    assert out.equals(fake_df)
    assert out is not fake_df  # must be a copy()

    (url,), kwargs = mock_read_csv.call_args
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/")
    assert "OECD.CFE.EDS,DSD_REG_ECO@DF_GDP," in url
    assert "/Q" in url
    assert "dimensionAtObservation=AllDimensions" in url
    assert "format=csvfile" in url
    assert kwargs["storage_options"]["User-Agent"]


def test_get_df_accepts_string_filter_expression_and_uppercases():
    calls._fetch_df.cache_clear()

    fake_df = pd.DataFrame({"x": [1]})
    with patch("notoecd.calls.pd.read_csv", return_value=fake_df) as mock_read_csv:
        _ = calls.get_df("A", "B", " tl2+tl3..gdp ")

    (url,), _ = mock_read_csv.call_args
    assert "/TL2+TL3..GDP" in url
