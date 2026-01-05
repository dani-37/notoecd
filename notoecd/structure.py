import requests
import pandas as pd
from functools import lru_cache
import xml.etree.ElementTree as ET

class Structure():
    def __init__(self, agencyID:str, dataflowID:str):
        self.ns = {
            'message': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
            'common': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
            'structure': 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
            'xml': 'http://www.w3.org/XML/1998/namespace'
        }

        url = f"https://sdmx.oecd.org/public/rest/dataflow/{agencyID}/{dataflowID}/?references=all"
        response = requests.get(url)
        tree = ET.ElementTree(ET.fromstring(response.content))
        self.root = tree.getroot()

        self.concepts = self.build_concepts_dict()
        self.values = self.build_values_dict()
        self.toc = self.build_toc()
        self.params = list(self.values.keys())

    def build_concepts_dict(self) -> dict:
        # Extract dimensions from the Concepts section
        concepts = {'DIMENSIONS':{}, 'CODELISTS':{}}
        conceptScheme_section = self.root.findall('.//message:Structures/structure:Concepts/structure:ConceptScheme', self.ns)
        if conceptScheme_section:
            for concept_scheme in conceptScheme_section:
                for concept in concept_scheme.findall('structure:Concept', self.ns):
                    concept_id = concept.get('id')
                    name_elem = concept.find('common:Name[@{http://www.w3.org/XML/1998/namespace}lang="en"]', self.ns)
                    if concept_id and name_elem is not None:
                        concepts['DIMENSIONS'][concept_id] = name_elem.text
                    for core_representation in concept.findall('structure:CoreRepresentation', self.ns):
                        for enumeration in core_representation.findall('structure:Enumeration', self.ns):
                            ref_elem = enumeration.find('Ref')
                            if ref_elem is not None:
                                codelist_id = ref_elem.get('id')
                                if concept_id and codelist_id:
                                    concepts['CODELISTS'][concept_id] = (
                                        codelist_id.split("CL_")[1] if codelist_id.startswith("CL_") 
                                        else codelist_id
                                    )
        
        # Extract codes from the Codelists section
        codes_section = self.root.findall('.//message:Structures/structure:Codelists/structure:Codelist', self.ns)
        if codes_section:
            for code_scheme in codes_section:
                dimension = code_scheme.get('id')[3:]
                concepts[dimension] = {}
                for code in code_scheme.findall('structure:Code', self.ns):
                    code_id = code.get('id')
                    name_elem = code.find('common:Name[@{http://www.w3.org/XML/1998/namespace}lang="en"]', self.ns)
                    if code_id and name_elem is not None:
                        concepts[dimension][code_id] = name_elem.text
        return concepts

    def build_values_dict(self) -> dict:
        # Extract values from Constraints section
        values = {}
        constraints_section = self.root.findall('.//message:Structures/structure:Constraints/structure:ContentConstraint', self.ns)
        if constraints_section:
            constraint = constraints_section[0]
            cube_region = constraint.find('structure:CubeRegion', self.ns)
            if cube_region is not None:
                for key_value in cube_region.findall('common:KeyValue', self.ns):
                    key = key_value.get('id')
                    value_elems = key_value.findall('common:Value', self.ns)
                    if key is not None and value_elems:
                        values[key] = [value_elem.text for value_elem in value_elems if value_elem.text]
        return values

    def build_toc(self) -> pd.DataFrame:
        # Builds a DataFrame containing the call dimensions and options (table of contents)
        data_structure = self.root.find('.//message:Structures/structure:DataStructures/structure:DataStructure', self.ns)
        dimension_list = data_structure.find('.//structure:DataStructureComponents/structure:DimensionList', self.ns)
        rows = []
        
        if dimension_list is not None:
            dimensions = dimension_list.findall('.//structure:Dimension', self.ns)
            
            # Sort dimensions by their 'position' to ensure correct order
            sorted_dimensions = sorted(dimensions, key=lambda dim: int(dim.get('position')))
            
            for dimension in sorted_dimensions:
                dimension_id = dimension.get('id')
                position = dimension.get('position')

                # Get the corresponding values for the dimension (if present in the 'values' dictionary)
                dimension_values = self.values.get(dimension_id, [])
                
                rows.append({
                    'id': int(position),
                    'title': dimension_id,
                    'values': dimension_values
                })

        df = pd.DataFrame(rows)
        df = df.sort_values(by='id').reset_index(drop=True)
        return df

    def explain_vals(self, dimension:str) -> dict:
        # Explains the parameters of a given dimension
        dimension = dimension.strip().upper()
        concepts = self.concepts
        values = self.values[dimension]
        codelists = concepts['CODELISTS']

        def fallback(dimension, concepts):
            # Look for subset of keys
            toc = self.toc
            concept_mapping = {}
            for title in toc.title:
                vals = set(toc[toc['title'] == title].values[0][2])
                concept_mapping[title] = [i for i in concepts.keys() if vals.issubset(set(concepts[i].keys()))][0]
            concept_mapping['FREQ'] = 'FREQ'
            if (dimension not in concepts) and (dimension in concept_mapping): 
                    dimension = concept_mapping[dimension]
            concepts = concepts[dimension]
            return {i: concepts[i] for i in values}

        if dimension not in codelists:
            if dimension in concepts: 
                return concepts[dimension]
            return fallback(dimension, concepts)
        
        dim_codelist = codelists[dimension]
        explanation = concepts[dim_codelist]
        clean_values = [i for i in values if i in explanation]

        if len(clean_values) == 0:
            return fallback(dimension, concepts)

        unclean_values = [i for i in values if i not in explanation]
        if len(unclean_values) > 0:
            print(f"Could not find explanation for {unclean_values}")

        return {i:explanation[i] for i in clean_values}

@lru_cache(maxsize=128)
def get_structure(agencyID: str, dataflowID: str) -> Structure:
    return Structure(agencyID, dataflowID)
