from knowledge_graph_base import (
    KNOWLEDGE_GRAPH_SAVING_PATH,
    construct_graph,
    save_graph,
)

from knowledge_graph_dependency import (
    add_conan_depends_on_relations,
    add_debian_depends_on_relations,
    add_deps_dev_depends_on_relations,
    add_github_depends_on_relations,
)
from knowledge_graph_hardware import add_hardware_version_relations, add_vendors
from knowledge_graph_software import (
    add_conan_software_version_relations,
    add_debian_software_version_relations,
    add_deps_dev_software_version_relations,
    add_github_software_version_relations,
)
from knowledge_graph_vulnerability import (
    add_cve_to_cwe_edges,
    add_deps_dev_advisory_vulnerability_relations,
    add_vulnerability_edges_for_assets,
)

VENDOR_LIST_FILE_PATH = "resources/cpe/vendors.csv"
VENDOR_WIKI_INFO_FILE_PATH = "resources/cpe/vendors_wikipedia_info.csv"

HARDWARE_VERSION_FILE_PATH = "resources/cpe/hardware_cpe_all.csv"

SOFTWARE_CONAN_VERSION_FILE_PATH = "resources/conan/conan_references.json"
SOFTWARE_DEBIAN_VERSION_FILE_PATH = (
    "resources/debian/debian_package_versions_in_cpp.json"
)
SOFTWARE_GITHUB_VERSION_FILE_PATH = "resources/github/github_package_versions.json"
SOFTWARE_GITHUB_REPO_INFO_FILE_PATH = "resources/github/github_repos_info_parsed.json"
SOFTWARE_PYTHON_VERSION_FILE_PATH = (
    "resources/deps-dev-data/python_package_versions.json"
)
SOFTWARE_RUST_VERSION_FILE_PATH = "resources/deps-dev-data/rust_packge_versions.json"

DEPS_CONAN_FILE_PATH = "resources/conan/conan_all_deps.csv"
DEPS_DEBIAN_FILE_PATH = "resources/debian/debian_all_deps.csv"
DEPS_GITHUB_FILE_PATH = "resources/github/github_all_deps.csv"
DEPS_PYTHON_1_FILE_PATH = "resources/deps-dev-data/python_deps_1.json"
DEPS_PYTHON_2_FILE_PATH = "resources/deps-dev-data/python_deps_2.json"
DEPS_RUST_FILE_PATH = "resources/deps-dev-data/rust_deps.json"

CVE_SOFTWARE_VERSION_FILE_PATH = "resources/cve/cve_software_versions.json"
CVE_HARDWARE_VERSION_FILE_PATH = "resources/cve/cve_hardware_versions.json"
CVE_TO_CWE_FILE_PATH = "resources/cve/all_cve.json"
DEPS_DEV_ADVISORIES_FILE_PATH = "resources/deps-dev-data/advisories.json"


def main():
    graph = construct_graph()
    add_vendors(graph, VENDOR_LIST_FILE_PATH, VENDOR_WIKI_INFO_FILE_PATH)
    add_hardware_version_relations(graph, HARDWARE_VERSION_FILE_PATH)

    add_conan_software_version_relations(graph, SOFTWARE_CONAN_VERSION_FILE_PATH)
    add_debian_software_version_relations(graph, SOFTWARE_DEBIAN_VERSION_FILE_PATH)
    add_github_software_version_relations(
        graph, SOFTWARE_GITHUB_VERSION_FILE_PATH, SOFTWARE_GITHUB_REPO_INFO_FILE_PATH
    )

    add_conan_depends_on_relations(graph, DEPS_CONAN_FILE_PATH)
    add_debian_depends_on_relations(
        graph, DEPS_DEBIAN_FILE_PATH, SOFTWARE_DEBIAN_VERSION_FILE_PATH
    )
    add_github_depends_on_relations(
        graph, DEPS_GITHUB_FILE_PATH, SOFTWARE_GITHUB_REPO_INFO_FILE_PATH
    )

    add_vulnerability_edges_for_assets(
        graph,
        CVE_SOFTWARE_VERSION_FILE_PATH,
        asset_kind="software",
    )
    add_vulnerability_edges_for_assets(
        graph,
        CVE_HARDWARE_VERSION_FILE_PATH,
        asset_kind="hardware",
    )

    add_cve_to_cwe_edges(graph, CVE_TO_CWE_FILE_PATH)
    # add_xz_utils_versions(graph)

    add_deps_dev_software_version_relations(
        graph, SOFTWARE_RUST_VERSION_FILE_PATH, "cargo"
    )
    add_deps_dev_software_version_relations(
        graph, SOFTWARE_PYTHON_VERSION_FILE_PATH, "pypi"
    )

    add_deps_dev_depends_on_relations(graph, DEPS_RUST_FILE_PATH, "cargo")
    add_deps_dev_depends_on_relations(graph, DEPS_PYTHON_1_FILE_PATH, "pypi")
    add_deps_dev_depends_on_relations(graph, DEPS_PYTHON_2_FILE_PATH, "pypi")


    add_deps_dev_advisory_vulnerability_relations(
        graph, SOFTWARE_RUST_VERSION_FILE_PATH, DEPS_DEV_ADVISORIES_FILE_PATH, "cargo"
    )
    add_deps_dev_advisory_vulnerability_relations(
        graph, SOFTWARE_PYTHON_VERSION_FILE_PATH, DEPS_DEV_ADVISORIES_FILE_PATH, "pypi"
    )

    print("Saving graph...")
    save_graph(graph, KNOWLEDGE_GRAPH_SAVING_PATH)


if __name__ == "__main__":
    main()
