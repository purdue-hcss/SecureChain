import pandas as pd
from knowledge_graph_constant import (
    NS,
    PROPERTY_HAS_HARDWARE_VERSION,
    PROPERTY_IDENTIFIER,
    PROPERTY_MANUFACTURER,
    PROPERTY_NAME,
    PROPERTY_URL,
    PROPERTY_VERSION_NAME,
    SCHEMA,
    hardware_uri,
    vendor_uri,
)
from rdflib import RDF, XSD, Graph, Literal
from tqdm import tqdm


def add_vendors(graph: Graph, vendor_list_file: str, vendor_wikipedia_info_file: str):
    df_basic = pd.read_csv(vendor_list_file).drop_duplicates("vendor")
    for row in tqdm(
        df_basic.itertuples(index=False), total=len(df_basic), desc="Adding vendors"
    ):
        raw_name = str(row.vendor).strip()
        vendor_ref = vendor_uri(raw_name)

        graph.add((vendor_ref, RDF.type, SCHEMA.Organization))
        graph.add((vendor_ref, PROPERTY_NAME, Literal(raw_name)))

    df_extra = pd.read_csv(vendor_wikipedia_info_file)
    for row in tqdm(
        df_extra.itertuples(index=False), total=len(df_extra), desc="Adding vendor info"
    ):
        raw_name = str(row.vendor).strip()
        vendor_ref = vendor_uri(raw_name)

        graph.add((vendor_ref, RDF.type, SCHEMA.Organization))
        graph.add((vendor_ref, PROPERTY_NAME, Literal(raw_name)))

        if pd.notna(row.wikidata_id):
            graph.add((vendor_ref, PROPERTY_IDENTIFIER, Literal(row.wikidata_id)))
        if pd.notna(row.urls):
            for u in str(row.urls).split("|"):
                graph.add(
                    (vendor_ref, PROPERTY_URL, Literal(u.strip(), datatype=XSD.anyURI))
                )


def add_hardware_version_relations(graph: Graph, hardware_version_file: str):
    df = pd.read_csv(hardware_version_file)
    df = df.groupby(["vendor", "product"])["version"].apply(list).reset_index()

    seen_hw = set()
    seen_ver = set()

    for row in tqdm(df.itertuples(index=False), desc="Adding hardware versions"):
        vendor_name = str(row.vendor).strip()
        product_name = str(row.product).strip()

        vendor_ref = vendor_uri(vendor_name)
        hardware_ref = hardware_uri(product_name)

        graph.add((vendor_ref, RDF.type, SCHEMA.Organization))

        if hardware_ref not in seen_hw:
            graph.add((hardware_ref, RDF.type, NS.Hardware))
            graph.add((hardware_ref, PROPERTY_NAME, Literal(product_name)))
            seen_hw.add(hardware_ref)

        graph.add((hardware_ref, PROPERTY_MANUFACTURER, vendor_ref))

        versions = row.version if isinstance(row.version, list) else [row.version]
        for ver in set(versions):
            ver_name = str(ver).strip()
            ver_uri = f"{product_name} {ver_name}"
            version_ref = hardware_uri(ver_uri)

            if version_ref not in seen_ver:
                graph.add((version_ref, RDF.type, NS.HardwareVersion))
                graph.add((version_ref, PROPERTY_VERSION_NAME, Literal(ver_name)))
                seen_ver.add(version_ref)

            graph.add((hardware_ref, PROPERTY_HAS_HARDWARE_VERSION, version_ref))
