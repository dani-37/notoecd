import importlib
import requests


def _fake_dataflow_all_xml() -> bytes:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
            <message:Structure
            xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
            xmlns:structure="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
            xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"
            xmlns:xml="http://www.w3.org/XML/1998/namespace"
            >
            <message:Structures>
                <structure:Dataflows>
                <structure:Dataflow id="DSD_REG_ECO@DF_GDP" agencyID="OECD.CFE.EDS">
                    <common:Name xml:lang="en">Gross domestic product - Regions</common:Name>
                    <common:Description xml:lang="en">GDP by region</common:Description>
                </structure:Dataflow>

                <structure:Dataflow id="DF_CAFE" agencyID="OECD.TEST">
                    <common:Name xml:lang="en">Café prices</common:Name>
                    <common:Description xml:lang="en">Prices in cafes</common:Description>
                </structure:Dataflow>

                <structure:Dataflow id="DF_OTHER" agencyID="OECD">
                    <common:Name xml:lang="en">Other dataset</common:Name>
                    <common:Description xml:lang="en">Other description</common:Description>
                </structure:Dataflow>
                </structure:Dataflows>
            </message:Structures>
            </message:Structure>
            """
    return xml.encode("utf-8")


class _Resp:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_datasets_lazy_loaded_and_cached_in_memory(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, *args, **kwargs):
        if url.endswith("/public/rest/dataflow/all"):
            calls["n"] += 1
            return _Resp(_fake_dataflow_all_xml())
        raise AssertionError(f"Unexpected URL in test_datasets: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    datasets_mod = importlib.import_module("notoecd.datasets")
    importlib.reload(datasets_mod)

    assert calls["n"] == 0

    hits = datasets_mod.search_keywords("gdp")
    assert calls["n"] == 1
    assert len(hits) == 1

    hits2 = datasets_mod.search_keywords("cafe")
    assert calls["n"] == 1
    assert len(hits2) == 1


def test_search_keywords_or_and_normalization(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/public/rest/dataflow/all"):
            return _Resp(_fake_dataflow_all_xml())
        raise AssertionError(f"Unexpected URL in test_datasets: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    datasets_mod = importlib.import_module("notoecd.datasets")
    importlib.reload(datasets_mod)

    hits = datasets_mod.search_keywords("gross domestic product", "cafe")

    assert len(hits) == 2
    assert any(hits["dataflowID"] == "DSD_REG_ECO@DF_GDP")
    assert any(hits["dataflowID"] == "DF_CAFE")

    names = " ".join(hits["name"].fillna("").tolist()).lower()
    assert ("gross domestic product" in names) or ("café" in names) or ("cafe" in names)


def test_search_keywords_rejects_empty(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if url.endswith("/public/rest/dataflow/all"):
            return _Resp(_fake_dataflow_all_xml())
        raise AssertionError(f"Unexpected URL in test_datasets: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    datasets_mod = importlib.import_module("notoecd.datasets")
    importlib.reload(datasets_mod)

    try:
        datasets_mod.search_keywords("   ", "")
        raise AssertionError("Expected ValueError for empty keywords")
    except ValueError:
        pass