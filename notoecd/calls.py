import pandas as pd
from typing import Union
from functools import lru_cache
from .structure import get_structure

@lru_cache(maxsize=256)
def _fetch_df(url: str) -> pd.DataFrame:
    return pd.read_csv(url, storage_options={"User-Agent": "Mozilla/5.0"})


def _clean(s: str) -> str: 
    return str(s).strip().lower()


def _build_filter_expression(
    agencyID: str,
    dataflowID: str,
    filters: dict,
) -> str:
    
    s = get_structure(agencyID, dataflowID)
    filters = {_clean(k): v for k, v in filters.items()}

    parts = []
    for dim in s.toc.title:
        dim_key = _clean(dim)
        if dim_key in filters:
            val = filters[dim_key]
            if isinstance(val, str):
                val = [val]
            parts.append("+".join(_clean(v) for v in val))
        else:
            parts.append("")

    return ".".join(parts).upper()


def get_df(
    agencyID: str,
    dataflowID: str,
    filters: Union[str, dict],
    version: str = "",
) -> pd.DataFrame:
    
    if isinstance(filters, dict):
        filter_expression = _build_filter_expression(agencyID, dataflowID, filters)
    else:
        filter_expression = _clean(filters).upper()

    url = (
        f"https://sdmx.oecd.org/public/rest/data/"
        f"{agencyID},{dataflowID},{version}/{filter_expression}"
        "?dimensionAtObservation=AllDimensions&format=csvfile"
    )

    base_df = _fetch_df(url)
    return base_df.copy()
