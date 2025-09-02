from rdflib import RDF, URIRef

def encoded_uri(ns: Namespace, uri: str) -> str:
    return ns[urllib.parse.quote_plus(uri)]


def rename_xz(software_name: str) -> str:
    if software_name == "xz" or software_name == "xz-utils":
        return "xz_utils"
    return software_name

def add_xz_utils_versions(g):
    xz_utils = URIRef(encoded_uri(SOFTWARE_NS, "xz_utils"))
    for version in ["5.4.6", "5.6.0", "5.6.1"]:
        version_ref = URIRef(SOFTWARE_VERSION_NS["xz_utils#" + version])
        g.add((version_ref, RDF.type, NS.SoftwareVersion))
        g.add((xz_utils, hasSoftwareVersion, version_ref))
        g.add((version_ref, versionName, Literal(version)))
    cve = URIRef(encoded_uri(CVE_NS, "CVE-2024-3094"))
    g.add((cve, RDF.type, NS.Vulnerability))
    g.add((cve, identifier, Literal("CVE-2024-3094")))
    g.add(
        (
            URIRef(SOFTWARE_VERSION_NS["xz_utils#" + urllib.parse.quote_plus("5.6.0")]),
            vulnerableTo,
            cve,
        )
    )
    g.add(
        (
            URIRef(SOFTWARE_VERSION_NS["xz_utils#" + urllib.parse.quote_plus("5.6.1")]),
            vulnerableTo,
            cve,
        )
    )
    g.add(
        (
            URIRef(SOFTWARE_VERSION_NS["xz_utils#" + urllib.parse.quote_plus("*")]),
            vulnerableTo,
            cve,
        )
    )

