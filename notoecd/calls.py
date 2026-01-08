import pandas as pd
from functools import lru_cache
from typing import Union, Optional
from .structure import get_structure

@lru_cache(maxsize=64)
def _fetch_df(url: str) -> pd.DataFrame:
    return pd.read_csv(url, storage_options={"User-Agent": "Mozilla/5.0"})


def _clean(s: str) -> str: 
    return str(s).strip().lower()


def _clean_dict(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        k = _clean(k)
        if isinstance(v, (list, tuple, set)):
            out[k] = [_clean(x) for x in v]
        else:
            out[k] = _clean(v)
    return out


def _build_filter_expression(
    agencyID: str,
    dataflowID: str,
    filters: dict,
) -> str:
    """
    Builds a valid OECD SDMX filter expression from a dictionary.
    
    Args:
        agencyID (str): The data provider agency identifier.
        dataflowID (str): The dataflow identifier within the agency.
        filters (dict): Dictionary with dimension names as keys and 
            either codes or labels as values.

    Returns 
        str: A valid OECD SDMX filter expression.
    """
    s = get_structure(agencyID, dataflowID)
    filters = _clean_dict(filters)
    
    parts = []
    for dim in s.toc.title:
        dim_key = _clean(dim)

        if dim_key in filters:
            val = filters[dim_key]
            concepts = _clean_dict(s.explain_vals(dim_key))
            rev = {v: k for k, v in concepts.items()}

            if isinstance(val, str): 
                val = [val]
            val = [_clean(v) for v in val]
            
            for i, v in enumerate(val):
                if v in concepts: continue
                if v in rev: val[i] = rev[v]
                else: raise ValueError(f"Invalid value '{v}' for dimension '{dim_key}'. ")

            parts.append("+".join(val))
        else:
            parts.append("")
    return ".".join(parts).upper()


def get_df(
    agencyID: str,
    dataflowID: str,
    filters: Union[str, dict] = "",
    version: str = "",
    startYear: Optional[int] = None,
    endYear: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetch data from the OECD SDMX API and return it as a pandas DataFrame.

    Args:
        agencyID (str): The data provider agency identifier.
        dataflowID (str): The dataflow identifier within the agency.
        filters (Union[str, dict], optional): Either a preformatted SDMX filter
            string or a dictionary of filters.
        version (str, optional): The dataflow version. Use an empty string for
            the latest version.
        startYear (int, optional): Start year (inclusive).
        endYear (int, optional): End year (inclusive).

    Returns:
        pd.DataFrame: The resulting dataset.
    """

    if isinstance(filters, dict):
        filter_expression = _build_filter_expression(agencyID, dataflowID, filters)
    else:
        filter_expression = _clean(filters).upper()

    url = (
        f"https://sdmx.oecd.org/public/rest/data/"
        f"{agencyID},{dataflowID},{version}/{filter_expression}"
        f"?dimensionAtObservation=AllDimensions&format=csvfile"
    )

    if startYear is not None: url += f"&startPeriod={startYear}"
    if endYear is not None: url += f"&endPeriod={endYear}"

    base_df = _fetch_df(url)
    return base_df.copy()
