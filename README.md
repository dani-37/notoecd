# notoecd

⚠️ **Unofficial package, not endorsed by the OECD.**

A lightweight Python interface for exploring OECD SDMX structures and downloading OECD datasets.

The package provides utilities for:

- Discovering dataset metadata
- Searching for relevant datasets using keyword matching
- Exploring the structure and code lists of a dataset
- Fetching filtered SDMX data directly into a pandas DataFrame

---

## Installation

You can install the package by running:

    pip install notoecd

---

## Quick Start

    import notoecd

The main functions in this module are:

    search_keywords(keywords) -> pd.DataFrame
    get_structure(agencyID, dataflowID) -> Structure
    get_df(agencyID, dataflowID, filters) -> pd.DataFrame

---

## Searching for datasets

`search_keywords` performs:

- Normalized text matching
- Accent-insensitive search
- Multi-keyword OR matching
- Ranking by number of matched keywords

Example:

    hits = notoecd.search_keywords('gross domestic product', 'tl2', 'tl3')

This returns datasets that mention GDP and regional levels (TL2/TL3). It gives their name, description, and identifiers (agencyID and dataflowID), which we will need for the next step.

---

## Inspecting dataset structure

Once a dataset is identified, load its SDMX structure:

    dataset = 'Gross domestic product - Regions'
    agencyID = 'OECD.CFE.EDS'
    dataflowID = 'DSD_REG_ECO@DF_GDP'

    s = notoecd.get_structure(agencyID, dataflowID)

### Table of contents

    s.toc

This shows all filters and their available values.

### Exploring code values

    s.explain_vals('MEASURE')
    s.explain_vals('UNIT_MEASURE')

This shows the available measures and units used in the dataset.

---

## Filtering and downloading data

To download data, build a dictionary of filters.  
Keys correspond to SDMX dimensions, values are strings or lists (for multiple values):

    filters = {
        'territorial_level': ['tl2', 'tl3'],
        'measure': 'gdp',
        'prices': 'Q',
        'unit_measure': 'USD_PPP_PS'
    }

Fetch the filtered dataset:

    df = notoecd.get_df(agency, dataflow, filters)
    df.head()

The returned object is a pandas DataFrame containing the requested subset of OECD SDMX data.

---

## Examples

You can see this full example as a notebook called example.ipynb.
