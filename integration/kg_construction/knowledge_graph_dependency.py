import json
import re
from typing import Dict, List
from urllib.parse import quote_plus
from debian.debian_support import Version
import pandas as pd
from rdflib import RDF, Graph, Literal, URIRef
from tqdm import tqdm

from knowledge_graph_constant import (
    DEPS_DEV_ECOSYSTEMS,
    NS,
    PROPERTY_DEPENDS_ON,
    PROPERTY_ECOSYSTEM,
    PROPERTY_HAS_SOFTWARE_VERSION,
    PROPERTY_NAME,
    PROPERTY_PROGRAMMING_LANGUAGE,
    PROPERTY_VERSION_NAME,
    conan_version_uri,
    debian_version_uri,
    deps_dev_pkg_uri,
    deps_dev_ver_uri,
    github_version_uri,
    google_search_uri,
)

_cmp_re: re.Pattern[str] = re.compile(r"^\s*(>=|<=|>>|<<|>|<|=)?\s*([^,&\s]+)\s*$")


def add_conan_depends_on_relations(graph: Graph, depends_csv_file: str) -> None:
    df = pd.read_csv(depends_csv_file)
    added_edges = set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding dependsOn edges"
    ):
        try:
            src_pkg, src_ver = str(row.Version).split("#", 1)
            tgt_pkg, tgt_ver = str(row.DependsOn).split("#", 1)
        except ValueError:
            print(f"[WARN] malformed line skipped: {row}")
            continue

        src_ref = conan_version_uri(src_pkg, src_ver)
        tgt_ref = conan_version_uri(tgt_pkg, tgt_ver)

        edge = (src_ref, PROPERTY_DEPENDS_ON, tgt_ref)
        if edge not in added_edges:
            graph.add(edge)
            added_edges.add(edge)


def add_debian_depends_on_relations(
    graph: Graph, depends_csv_file: str, debian_pkg_versions_file: str
) -> None:
    with open(debian_pkg_versions_file, encoding="utf-8") as f:
        version_map: Dict[str, List[str]] = json.load(f)

    df = pd.read_csv(depends_csv_file)

    edge_seen: set[tuple] = set()
    tgt_node_seen: set[URIRef] = set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding Debian dependsOn edges"
    ):
        try:
            src_pkg, src_ver = str(row.Version).split("#", 1)
            tgt_pkg, tgt_expr = str(row.DependsOn).split("#", 1)
        except ValueError:
            print(f"[WARN] malformed line skipped: {row}")
            continue

        src_uri = debian_version_uri(src_pkg, src_ver)

        try:
            constraints = parse_constraints(tgt_expr)
        except ValueError as e:
            print("[WARN]", e)
            continue

        all_tgt_versions = version_map.get(tgt_pkg, [])
        matches = [v for v in all_tgt_versions if satisfies(v, constraints)]

        if not matches:
            continue

        for v in matches:
            tgt_uri = debian_version_uri(tgt_pkg, v)

            # 必要时为目标版本补 type、versionName（可选）
            if tgt_uri not in tgt_node_seen:
                # print(f"[INFO] add {tgt_uri} to graph")
                graph.add((tgt_uri, RDF.type, NS.SoftwareVersion))
                graph.add((tgt_uri, PROPERTY_VERSION_NAME, Literal(v)))
                tgt_node_seen.add(tgt_uri)

            triple = (src_uri, PROPERTY_DEPENDS_ON, tgt_uri)
            if triple not in edge_seen:
                graph.add(triple)
                edge_seen.add(triple)


def add_github_depends_on_relations(
    graph: Graph, depends_csv_file: str, github_repo_meta_file: str
) -> None:
    with open(github_repo_meta_file, encoding="utf-8") as f:
        meta_map = json.load(f)

    def repo_url_of(key: str) -> str:
        return meta_map.get(key, {}).get(
            "repository_url", f"https://github.com/{quote_plus(key, safe='.-_')}"
        )

    df = pd.read_csv(depends_csv_file)  # Version,DependsOn

    seen_soft, seen_ver, seen_edge = set(), set(), set()

    for row in tqdm(
        df.itertuples(index=False), total=len(df), desc="Adding GitHub dependsOn edges"
    ):
        try:
            src_pkg, src_tag = str(row.Version).split("#", 1)
            tgt_pkg, tgt_tag = str(row.DependsOn).split("#", 1)
        except ValueError:
            continue  # 格式不符

        # ---------- 源版本 URI（已在图中） -------------------------
        src_uri = github_version_uri(repo_url_of(src_pkg), src_tag)

        # ---------- 目标 Software 节点 ----------------------------
        tgt_soft_uri = google_search_uri(tgt_pkg)
        if tgt_soft_uri not in seen_soft:
            graph.add((tgt_soft_uri, RDF.type, NS.Software))
            graph.add((tgt_soft_uri, PROPERTY_NAME, Literal(tgt_pkg)))
            graph.add((tgt_soft_uri, PROPERTY_PROGRAMMING_LANGUAGE, Literal("C/C++")))
            graph.add((tgt_soft_uri, PROPERTY_ECOSYSTEM, Literal("Unknown")))
            seen_soft.add(tgt_soft_uri)

        # -- 目标 SoftwareVersion --
        tgt_ver_uri = google_search_uri(tgt_pkg, tgt_tag)
        if tgt_ver_uri not in seen_ver:
            graph.add((tgt_ver_uri, RDF.type, NS.SoftwareVersion))
            graph.add((tgt_ver_uri, PROPERTY_VERSION_NAME, Literal(tgt_tag)))
            graph.add((tgt_soft_uri, PROPERTY_HAS_SOFTWARE_VERSION, tgt_ver_uri))
            seen_ver.add(tgt_ver_uri)

        # -- dependsOn 边 --
        edge = (src_uri, PROPERTY_DEPENDS_ON, tgt_ver_uri)
        if edge not in seen_edge:
            graph.add(edge)
            seen_edge.add(edge)


def parse_constraints(expr: str):
    """
    把 '>=1.2&<2.0' or '1.4.2' or '*' 拆成 [(op, ver), ...].
    '*' → [('*', None)]
    无符号 → '='
    支持 & 或 , 作为 AND 连接
    """
    expr = expr.strip()
    if expr == "*" or expr == "":
        return [("*", None)]

    clauses = re.split(r"[&,]", expr)
    out = []
    for cl in clauses:
        m = _cmp_re.match(cl)
        if not m:
            raise ValueError(f"cannot parse constraint: {cl}")
        op = m.group(1) or "="
        ver = m.group(2)
        out.append((op, ver))
    return out


def satisfies(ver: str, constraints) -> bool:
    """ver: candidate version str; constraints: [(op, ver2), ...]"""
    v = Version(ver)
    for op, rhs in constraints:
        if op == "*" or (op in ("=", "==") and rhs == "*"):
            return True
        cmp = cmp_version_obj(v, Version(rhs))
        if (
            (op in ("=", "==") and cmp != 0)
            or (op in (">", ">>") and cmp <= 0)  # ← 新增  >>
            or (op in ("<", "<<") and cmp >= 0)  # ← 新增  <<
            or (op == ">=" and cmp < 0)
            or (op == "<=" and cmp > 0)
        ):
            return False
    # print(f"version {ver} satisfies constraints {constraints}")
    return True


def cmp_version_obj(va: Version, vb: Version) -> int:
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def add_deps_dev_depends_on_relations(
    g: Graph, deps_jsonl_path: str, ecosystem: str
) -> None:
    cfg = DEPS_DEV_ECOSYSTEMS[ecosystem]
    seen_soft, seen_ver, seen_edge = set(), set(), set()

    with open(deps_jsonl_path, encoding="utf-8") as f:
        for line in tqdm(f, desc=f"Adding {ecosystem} dependsOn edges"):
            rec = json.loads(line)
            frm = rec["From"]
            to = rec["To"]

            if (
                frm.get("System") != ecosystem.upper()
                or to.get("System") != ecosystem.upper()
            ):
                continue

            fname, fver = frm["Name"].strip(), frm["Version"].strip()
            tname, tver = to["Name"].strip(), to["Version"].strip()

            frm_uri = deps_dev_ver_uri(ecosystem, fname, fver)

            tsoft_uri = deps_dev_pkg_uri(ecosystem, tname)
            if tsoft_uri not in seen_soft:
                g.add((tsoft_uri, RDF.type, NS.Software))
                g.add((tsoft_uri, PROPERTY_NAME, Literal(tname)))
                g.add((tsoft_uri, PROPERTY_PROGRAMMING_LANGUAGE, Literal(cfg["lang"])))
                g.add((tsoft_uri, PROPERTY_ECOSYSTEM, Literal(cfg["eco"])))
                seen_soft.add(tsoft_uri)

            tver_uri = deps_dev_ver_uri(ecosystem, tname, tver)
            if tver_uri not in seen_ver:
                g.add((tver_uri, RDF.type, NS.SoftwareVersion))
                g.add((tver_uri, PROPERTY_VERSION_NAME, Literal(tver)))
                g.add((tsoft_uri, PROPERTY_HAS_SOFTWARE_VERSION, tver_uri))
                seen_ver.add(tver_uri)

            edge = (frm_uri, PROPERTY_DEPENDS_ON, tver_uri)
            if edge not in seen_edge:
                g.add(edge)
                seen_edge.add(edge)
