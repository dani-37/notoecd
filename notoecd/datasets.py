import re
import html
import requests
import unicodedata
import pandas as pd
import xml.etree.ElementTree as ET

url = "https://sdmx.oecd.org/public/rest/dataflow/all"

NS = {
    "message": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message",
    "structure": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "common": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
    "xml": "http://www.w3.org/XML/1998/namespace",
}

_ws_re = re.compile(r"\s+")
_tag_re = re.compile(r"<[^>]+>")

def _clean(s: str | None) -> str | None:
    if s is None: return None
    s = html.unescape(s)
    s = _tag_re.sub("", s)
    s = _ws_re.sub(" ", s).strip()
    return s or None

# Cache
_datasets: pd.DataFrame | None = None

def _load_datasets() -> pd.DataFrame:
    """
    Loads OECD datasets and keeps them in memory.
    """
    global _datasets
    if _datasets is not None: return _datasets

    headers = {"Accept": "application/vnd.sdmx.structure+xml;version=2.1"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    rows = []
    for df in root.findall(".//structure:Dataflow", NS):
        dataflow_id = df.attrib.get("id")
        agency_id = df.attrib.get("agencyID")

        name_elem = df.find("common:Name[@xml:lang='en']", NS)
        desc_elem = df.find("common:Description[@xml:lang='en']", NS)

        name = _clean("".join(name_elem.itertext())) if name_elem is not None else None
        desc_raw = "".join(desc_elem.itertext()) if desc_elem is not None else None
        desc = _clean(desc_raw)

        rows.append(
            {
                "dataflowID": dataflow_id,
                "agencyID": agency_id,
                "name": name,
                "description": desc,
            }
        )

    _datasets = pd.DataFrame(rows)
    return _datasets

def search_keywords(*keywords: str) -> pd.DataFrame:
    """
    Searches OECD datasets for a set of keywords.

    Args:
        *keywords (str): One or more keywords. Acts as OR.

    Returns:
        pd.DataFrame: Matching rows.
    """
    datasets = _load_datasets()

    # Clean and validate keywords
    keywords = [k for k in keywords if isinstance(k, str) and k.strip()]
    if not keywords:
        raise ValueError("No valid keywords provided.")

    def _normalize_series(s: pd.Series) -> pd.Series:
        s = s.fillna("").astype(str).str.lower()
        return s.map(
            lambda x: "".join(
                ch for ch in unicodedata.normalize("NFKD", x)
                if not unicodedata.combining(ch)
            )
        )

    text = (
        datasets["name"].fillna("").astype(str)
        + " "
        + datasets["description"].fillna("").astype(str)
    )
    text_norm = _normalize_series(text)
    name_norm = _normalize_series(datasets["name"])

    def _normalize_kw(kw: str) -> str:
        kw = unicodedata.normalize("NFKD", kw.lower())
        return "".join(ch for ch in kw if not unicodedata.combining(ch))

    norm_keywords = [_normalize_kw(k) for k in keywords]

    overall_mask = pd.Series(False, index=datasets.index)
    score = pd.Series(0, index=datasets.index, dtype="int64")

    for kw in norm_keywords:
        m = text_norm.str.contains(kw, na=False, regex=False)
        mt = name_norm.str.contains(kw, na=False, regex=False)
        overall_mask |= m
        score = score.add(m.astype("int8"), fill_value=0) + mt.astype("int8")

    result = datasets.loc[overall_mask].copy()
    result["_match_score"] = score.loc[overall_mask]
    result = result.sort_values("_match_score", ascending=False)

    return result[["agencyID", "dataflowID", "name", "description"]]