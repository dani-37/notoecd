import importlib
import requests
import pandas as pd


def _fake_structure_xml() -> bytes:
    return  b"""<?xml version="1.0" encoding="UTF-8"?>
                <message:Structure
                xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
                xmlns:structure="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
                xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"
                xmlns:xml="http://www.w3.org/XML/1998/namespace"
                >
                <message:Structures>

                    <structure:Concepts>
                    <structure:ConceptScheme>
                        <structure:Concept id="PRICES">
                        <common:Name xml:lang="en">Prices</common:Name>
                        <structure:CoreRepresentation>
                            <structure:Enumeration>
                            <Ref id="CL_PRICES"/>
                            </structure:Enumeration>
                        </structure:CoreRepresentation>
                        </structure:Concept>
                    </structure:ConceptScheme>
                    </structure:Concepts>

                    <structure:Codelists>
                    <structure:Codelist id="CL_PRICES">
                        <structure:Code id="Q">
                        <common:Name xml:lang="en">Quarterly</common:Name>
                        </structure:Code>
                        <structure:Code id="V">
                        <common:Name xml:lang="en">Volume</common:Name>
                        </structure:Code>
                    </structure:Codelist>
                    </structure:Codelists>

                    <structure:Constraints>
                    <structure:ContentConstraint>
                        <structure:CubeRegion>
                        <common:KeyValue id="PRICES">
                            <common:Value>Q</common:Value>
                            <common:Value>V</common:Value>
                        </common:KeyValue>
                        </structure:CubeRegion>
                    </structure:ContentConstraint>
                    </structure:Constraints>

                    <structure:DataStructures>
                    <structure:DataStructure>
                        <structure:DataStructureComponents>
                        <structure:DimensionList>
                            <structure:Dimension id="PRICES" position="1"/>
                        </structure:DimensionList>
                        </structure:DataStructureComponents>
                    </structure:DataStructure>
                    </structure:DataStructures>

                </message:Structures>
                </message:Structure>
                """


class _Resp:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


def test_get_structure_builds_toc_values_and_explain(monkeypatch):
    def fake_get(url, *args, **kwargs):
        if "/public/rest/dataflow/" in url and "?references=all" in url:
            return _Resp(_fake_structure_xml())
        raise AssertionError(f"Unexpected URL in test_structure: {url}")

    # Patch the requests used by notoecd.structure
    monkeypatch.setattr(requests, "get", fake_get)

    structure_mod = importlib.import_module("notoecd.structure")
    importlib.reload(structure_mod)

    # Clear cache so test is isolated
    structure_mod.get_structure.cache_clear()

    s = structure_mod.get_structure("OECD.CFE.EDS", "DSD_REG_ECO@DF_GDP")

    assert isinstance(s.toc, pd.DataFrame)
    assert list(s.toc["title"]) == ["PRICES"]
    assert s.toc.loc[0, "values"] == ["Q", "V"]

    assert isinstance(s.concepts, dict)
    assert "CODELISTS" in s.concepts
    assert "PRICES" in s.concepts

    d = s.explain_vals("PRICES")
    assert d == {"Q": "Quarterly", "V": "Volume"}
