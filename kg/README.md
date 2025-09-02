# ⛓️ Secure Chain Knowledge Graph Data

This directory contains information and access points for the **Secure Chain Knowledge Graph** data dump.

## ℹ️ Introduction

The Secure Chain Knowledge Graph is a comprehensive knowledge graph designed to model the relationships between **software, software versions, hardware, hardware versions, vulnerabilities (CVE), vulnerability types (CWE), licenses, dependencies, vendors**, and other entities to support secure and transparent management of software supply chains.

The model extends our public ontology: **[Secure Chain Ontology](https://purdue-hcss.github.io/secure-chain-ontology/)**.

  * **Namespace (prefix `sc:`)**: `https://w3id.org/secure-chain/`

  * **Also uses**: `schema:` → `http://schema.org/`

  * **Typical output format**: N-Triples (`.nt`)

## 📚 Accessing the Knowledge Graph

You can access the knowledge graph data in two ways: by downloading the complete data dump or by querying our live SPARQL endpoint.

### 💾 Data Dump

The complete RDF data dump is available for download via Google Drive. We recommend using this for offline analysis or to load the data into your own triplestore.

  * **Download Link**: **[Google Drive](https://drive.google.com/file/d/1SJP6KtGNvhcxdFFOi1c3st28bDLiPnA6/view?usp=drive_link)**

### 🌐 Live SPARQL Query Interface

For an interactive experience, you can use our web-based query interface to run live SPARQL queries directly against the knowledge graph.

  * **Query Interface**: **[Run Live SPARQL Queries](https://frink.apps.renci.org/?query=PREFIX%20rdf%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F1999%2F02%2F22-rdf-syntax-ns%23%3E%0APREFIX%20rdfs%3A%20%3Chttp%3A%2F%2Fwww.w3.org%2F2000%2F01%2Frdf-schema%23%3E%0ASELECT%20*%20WHERE%20%7B%0A%20%20%3Fsub%20%3Fpred%20%3Fobj%20.%0A%7D%20LIMIT%2010&sources=%5B%22securechainkg%22%5D)**

### 🔌 SPARQL Endpoint (for Programmatic Access)

For programmatic access and integration with other tools, you can use our public SPARQL endpoint.

  * **Endpoint URL**: **`https://frink.apps.renci.org/securechainkg/sparql`**

### 📜 Ontology Documentation

To understand the schema, classes, and properties used in the knowledge graph, please refer to our ontology documentation.

  * **Ontology Docs**: **[Ontology Documentation](https://purdue-hcss.github.io/secure-chain-ontology/)**

## 🏗️ Ontology Design

The Secure Chain Ontology is the blueprint for our knowledge graph. We use `sc:Software` as a central concept to represent software, with associated `sc:SoftwareVersions` capturing its evolution. These versions are critical for tracking vulnerabilities and dependencies. The ontology models relationships between components, such as `sc:dependsOn` and `sc:OperatesOn`, to help assess risks.

Additionally, `sc:License` links software to its legal aspects, `sc:Hardware` and `sc:HardwareVersions` extend tracking to physical components, and `sc:Vulnerability` provides a detailed view of security risks.

![Ontology Design](https://purdue-hcss.github.io/nsf-software-supply-chain_security/images/image12.png)

## 🚀 Usage Example (with Data Dump)

The data dumps are formatted as RDF, making them compatible with most Semantic Web tools and triplestores.

### ▶️ Getting Started

1.  **Download the Data**: Get the latest RDF data dump from the **[Google Drive link](https://drive.google.com/file/d/1SJP6KtGNvhcxdFFOi1c3st28bDLiPnA6/view?usp=drive_link)**.

2.  **Load into a Triplestore**: Use a knowledge graph tool to load the data. For example:

      * **Apache Jena (Fuseki)**: Use the following commands to start a local Fuseki server and upload the data:
        ```bash
        # Start a local Fuseki (example)
        docker run -it --rm -p 3030:3030 stain/jena-fuseki

        # In the Fuseki UI, create a dataset and upload the .nt file you downloaded.
        ```
      * **RDFLib (Python)**: Load the graph directly in your Python script:
        ```python
        import rdflib
        g = rdflib.Graph()
        g.parse("path/to/secure-chain.nt", format="nt")
        print(f"Graph loaded with {len(g)} statements.")
        ```

3.  **Explore and Query**: Use SPARQL queries to explore relationships within the Secure Chain Knowledge Graph.

### ✨ Examples (SPARQL)

> Tip: Names in the data come from different ecosystems (Conan, Debian, GitHub, deps.dev). If you don’t know a node’s URI, **search by name** and then join to versions/edges.

#### 1) CVEs that affect a given software *name* and *version label*

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?softwareName ?versionLabel ?cveId
WHERE {
  ?soft a sc:Software ;
        schema:name ?softwareName .
  FILTER(LCASE(?softwareName) = "xz-utils")    # change as needed

  ?soft sc:hasSoftwareVersion ?ver .
  ?ver  sc:versionName        ?versionLabel .
  FILTER(?versionLabel = "5.6.0")              # change as needed

  ?ver  sc:vulnerableTo ?cve .
  ?cve  schema:identifier ?cveId .
}
ORDER BY ?cveId
```

#### 2) Dependency edges (what a version depends on)

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?srcName ?srcVer ?tgtName ?tgtVer
WHERE {
  ?soft a sc:Software ; schema:name ?srcName .
  FILTER(LCASE(?srcName) = "openssl")          # example

  ?soft sc:hasSoftwareVersion ?v1 .
  ?v1   sc:versionName ?srcVer .

  ?v1   sc:dependsOn ?v2 .
  ?soft2 a sc:Software ; sc:hasSoftwareVersion ?v2 ; schema:name ?tgtName .
  ?v2   sc:versionName ?tgtVer .
}
LIMIT 100
```

#### 3) Software versions that operate on a particular hardware version

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?swName ?swVer ?hwName ?hwVer
WHERE {
  ?hw a sc:Hardware ; schema:name ?hwName .
  FILTER(CONTAINS(LCASE(?hwName), "iphone"))   # broad match example

  ?hw sc:hasHardwareVersion ?hv .
  ?hv sc:versionName ?hwVer .

  ?sv a sc:SoftwareVersion ;
      sc:operatesOn ?hv ;
      sc:versionName ?swVer .

  ?sw a sc:Software ;
      sc:hasSoftwareVersion ?sv ;
      schema:name ?swName .
}
LIMIT 100
```

#### 4) CVE → CWE linking (vulnerability types)

```sparql
PREFIX sc:     <https://w3id.org/secure-chain/>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?cveId ?cweId
WHERE {
  ?cve a sc:Vulnerability ; schema:identifier ?cveId .
  ?cve sc:vulnerabilityType ?cwe .
  ?cwe schema:identifier ?cweId .
}
ORDER BY ?cveId ?cweId
```

## 🗺️ Model Overview

The Secure Chain Ontology **builds on top of `schema.org`**, extending it to capture supply-chain-specific relations.

Key classes:

* `sc:Software`, `sc:SoftwareVersion`
* `sc:Hardware`, `sc:HardwareVersion`
* `sc:Vulnerability` (e.g., CVE), `sc:VulnerabilityType` (e.g., CWE)
* `sc:License`

Key properties:

* `sc:hasSoftwareVersion (Software → SoftwareVersion)`
* `sc:hasHardwareVersion (Hardware → HardwareVersion)`
* `sc:dependsOn (SoftwareVersion → SoftwareVersion)`
* `sc:operatesOn (SoftwareVersion → HardwareVersion)`
* `sc:vulnerableTo (SoftwareVersion → Vulnerability)`
* `sc:vulnerabilityType (Vulnerability → VulnerabilityType)`
* `sc:versionName (SoftwareVersion/HardwareVersion → Text)`
* `schema:name`, `schema:identifier`, `schema:license`, `schema:url`, `schema:contributor`, `schema:programmingLanguage`, `schema:manufacturer`

For the complete ontology and definitions, see the documentation linked above.

## 🙏 Attribution & License

The KG integrates information derived from multiple public sources (e.g., NVD CVE, CPE, Debian, ConanCenter, GitHub, deps.dev, Wikipedia/Wikidata/DBpedia, etc.).
This repository is licensed under **Apache License 2.0**. See the root [`LICENSE`](../LICENSE).

If you use the Secure Chain KG in research or tooling, a citation or link back is appreciated.
