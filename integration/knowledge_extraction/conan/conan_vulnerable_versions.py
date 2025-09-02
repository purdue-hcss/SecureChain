import json

# ① 载入你的 repology 文件
with open("conan/vulnerable_versions_conan_from_repology.json", "r", encoding="utf-8") as f:
    repology = json.load(f)

# ② 收集满足条件的 (包名, 版本) 二元组
vuln_conan = [
    (pkg, entry["version"])
    for pkg, entries in repology.items()
    for entry in entries
    if entry.get("repo") == "conancenter" and entry.get("vulnerable", False)
]

# ③ 输出 / 后续处理
for name, ver in vuln_conan:
    print(f"{name} {ver}")

print(f"Total: {len(vuln_conan)}")