import notoecd

def test_public_api_exports():
    assert callable(notoecd.get_df)
    assert callable(notoecd.get_structure)
    assert callable(notoecd.search_keywords)

def test_import_package():
    import importlib
    m = importlib.import_module("notoecd")
    assert m is not None
