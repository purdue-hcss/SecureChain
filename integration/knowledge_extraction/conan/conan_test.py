#!/usr/bin/env python3
"""json2conanlist.py  ——  读取 conancenter_all_versions.json
    生成 conanfile_ALL.txt，其 [requires] 段列出所有 <pkg>/<ver>"""

import json, pathlib

JSON_IN  = "conancenter_all_versions.json"
TXT_OUT  = "conanfile_ALL.txt"
SORT     = True          # 是否排序：True=字典序 / False=保持 JSON 原顺序
# --- 若想按 semver 排序，取消下面两行注释 ---
# from packaging.version import Version
# SORT_KEY = lambda s: (s.split('/')[0], Version(s.split('/')[1]))

# 1) 读取
data = json.loads(pathlib.Path(JSON_IN).read_text(encoding="utf-8"))
refs = list(data["conancenter"].keys())

# 2) 排序（可选）
if SORT:
    refs.sort()          # 简单字典序
    # refs.sort(key=SORT_KEY)    # semver 排序

# 3) 写文件
requires_block = "\n".join(refs)
tpl = f"""# THIS FILE IS **NOT** FOR DIRECT CONAN INSTALL\n# It just lists every package/version in conancenter\n\n[requires]\n{requires_block}\n"""
pathlib.Path(TXT_OUT).write_text(tpl, encoding="utf-8")
print(f"✅  List written to {TXT_OUT}  (total {len(refs)} lines)")
