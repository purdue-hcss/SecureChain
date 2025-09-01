# ⚙️ Data Integration Pipeline

This folder contains the complete data processing pipeline for the **SecureChain Knowledge Graph** from raw ecosystem data. The scripts here are responsible for collecting raw data from diverse sources, processing it, and assembling it into the final RDF knowledge graph.

```
integration/
├─ kg_construction/       # Build the graph from prepared resources
├─ knowledge_extraction/  # Scripts to collect/normalize input data
└─ relation_extraction/   # Entity & relationship extraction (UniNER / WikiSER / LLM glue)
```

The pipeline follows a three-stage workflow:

1.  **Knowledge Extraction**: Gathers data from structured and semi-structured sources.
2.  **Relation Extraction**: Extracts entities and relationships from unstructured text using NER models.
3.  **Knowledge Graph Construction**: Maps the extracted data to our ontology and builds the final graph.

## 🗂️ Directories

### 📁 `knowledge_extraction/`

This module focuses on collecting information from well-defined, structured sources. Each script is tailored to a specific data provider, such as package managers, code repositories, and security databases.

* **Key Responsibilities**:
    * Crawling package metadata from **Conan**, **Debian**, and **GitHub**.
    * Parsing security advisories and product information from **NVD**, including **CVE**, **CPE**, and **CWE** databases.
    * Enriching entities by matching them with external knowledge bases like **Wikipedia** and **DBpedia**.
* **Output**: A collection of processed, intermediate data files (usually in CSV or JSON format) ready for the construction phase.

### 📁 `relation_extraction/`

This module complements the first stage by targeting **unstructured text sources** like security blogs, bug reports, and developer discussions. It uses state-of-the-art Natural Language Processing (NLP) techniques to discover entities and relationships that are not available in structured databases.

* **Key Technologies**:
    * **Named Entity Recognition (NER)** to identify software, hardware, and vulnerabilities mentioned in the text.
    * **Large Language Models (LLMs)**, such as Llama3, to understand context and extract complex relationships between entities.
* **Output**: Structured relational data extracted from raw text, which enriches the knowledge graph with deeper, contextual insights.

### 📁 `kg_construction/`

This is the final stage of the pipeline, where all the processed information comes together. These scripts take the data from both `knowledge_extraction` and `relation_extraction` and transform it into a unified, queryable knowledge graph.

* **Key Responsibilities**:
    * Defining the graph's **ontology** (classes and properties) using RDF and OWL.
    * Mapping all extracted data points to the defined ontology.
    * Generating the final, consolidated knowledge graph as a single **RDF file** (in N-Triples format).
* **Output**: The `secure-chain.nt` file, which is the complete SecureChain Knowledge Graph.

## 📜 License

Code in this repo is licensed under **Apache License 2.0**. See the root [`LICENSE`](../LICENSE).

Subfolders under `relation_extraction/UniNER/universal-ner/` include third-party files with their own licenses (see the `LICENSE` files in those directories). Upstream data and model artifacts remain subject to their respective licenses/terms.
