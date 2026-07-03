"""VBA 工具代码生成器。

读取 tools/vba_defs/*.toml → 生成 scripts/cst_runtime/tools/gen_*.py

用法:
    cd skills/cst-runtime-cli
    uv run python tools/generate_tools.py

每次修改 TOML 后手动运行。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

# ── 配置 ──────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent
DEFS_DIR = HERE / "vba_defs"
OUTPUT_DIR = HERE.parent.parent.parent / "devkit" / "tools" / "generated"

HEADER = '''"""自动生成 — 请勿手改。运行 tools/generate_tools.py 重新生成。"""

from __future__ import annotations

from enum import Enum
from typing import Any


def _q(v: Any) -> str:
    """VBA 加引号"""
    return f'"{v}"'


def _v(v: Any) -> str:
    """VBA 不加引号"""
    return str(v)
'''

_QUOTED = {"str"}
_UNQUOTED = {"float", "int", "bool", "expr"}


# ── 工具函数 ──────────────────────────────────────────────


def _snake(name: str) -> str:
    s = re.sub(r"([A-Z])", r"_\1", name).lower().lstrip("_")
    return re.sub(r"[_\s]+", "_", s)


def _kebab(name: str) -> str:
    return name.lower().replace(" ", "-").replace("_", "-")


def _type_hint(toml_type: str, enums: set[str]) -> str:
    if toml_type in enums:
        return toml_type
    return {"str": "str", "float": "float", "int": "int", "bool": "bool", "expr": "str"}.get(toml_type, "str")


def _param_default(p: dict) -> str:
    if "default" not in p:
        return ""
    val = p["default"]
    ptype = p.get("type", "str")
    if ptype == "bool":
        # TOML 中 default="true"/"false" → Python True/False
        return "True" if str(val).lower() == "true" else "False"
    if ptype == "str":
        return f'"{val}"'
    if ptype in _UNQUOTED:
        return str(val)
    # enum
    member = re.sub(r"[\s\-\+]+", "_", str(val))
    member = re.sub(r"[()]", "", member)
    member = member.strip("_").upper()
    if member and member[0].isdigit():
        member = f"_{member}"
    return f"{ptype}.{member}"


def _vba_ref(param_name: str, param_type: str, enums: set[str]) -> str:
    """返回在 f-string 模板中使用的参数引用（不含外层花括号）。"""
    if param_type in enums:
        return f"{param_name}.value"
    return param_name


def _is_quoted(param_type: str, enums: set[str]) -> bool:
    return param_type in _QUOTED or param_type in enums


def _collect_params(methods: list[dict]) -> list[dict]:
    """收集非 hardcoded 的参数（required 在前，带默认值的在后）。

    允许同名同类型合并；同名不同类型报错；同名不同默认值报错。"""
    seen: dict[str, dict] = {}
    required = []
    optional = []

    def _add(p: dict) -> None:
        pname = p["name"]
        ptype = p.get("type", "str")
        pdefault = p.get("default")

        if pname in seen:
            existing = seen[pname]
            if existing.get("type", "str") != ptype:
                raise ValueError(
                    f"Param '{pname}' has conflicting types: "
                    f"'{existing.get('type')}' (from '{existing['_mname']}') vs "
                    f"'{ptype}' (from '{p['_mname']}')"
                )
            if existing.get("default") != pdefault:
                raise ValueError(
                    f"Param '{pname}' has conflicting defaults: "
                    f"'{existing.get('default')}' vs '{pdefault}'"
                )
            return  # dup with same type/default → skip

        seen[pname] = p
        if "default" in p:
            optional.append(p)
        else:
            required.append(p)

    for m in methods:
        for p in m.get("params", []):
            if p.get("hardcoded"):
                continue
            p["_mname"] = m["name"]  # attach for error messages
            _add(p)

    return required + optional


def _build_sig(all_params: list[dict], enums: set[str]) -> str:
    parts = ["project: Any"]
    for p in all_params:
        hint = _type_hint(p.get("type", "str"), enums)
        d = _param_default(p)
        if d:
            parts.append(f"{p['name']}: {hint} = {d}")
        else:
            parts.append(f"{p['name']}: {hint}")
    return ", ".join(parts)


def _build_params_desc(all_params: list[dict]) -> dict:
    result = {}
    for p in all_params:
        entry: dict = {"type": p.get("type", "str"), "required": "default" not in p, "description": p.get("description", p["name"])}
        if "default" in p:
            entry["default"] = p["default"]
        result[p["name"]] = entry
    return result


# ── 代码生成 ──────────────────────────────────────────────


def gen_enums(enums: dict) -> list[str]:
    lines = []
    for ename, edef in enums.items():
        lines.append(f"class {ename}(Enum):")
        for v in edef.get("values", []):
            member = re.sub(r"[\s\-\+]+", "_", v)
            member = re.sub(r"[()]", "", member)
            member = member.strip("_").upper()
            if member and member[0].isdigit():
                member = f"_{member}"
            lines.append(f'    {member} = "{v}"')
        lines.append("")
    return lines


def gen_block_fn(obj: dict, block_methods: list[dict], enums: dict) -> list[str]:
    vba_obj = obj.get("vba_object", obj["name"])
    obj_name = obj["name"]
    categories = obj.get("categories", [])

    all_params = _collect_params(block_methods)
    enum_names = set(enums.keys())
    sig = _build_sig(all_params, enum_names)

    prefix = ""
    if categories:
        prefix = categories[0].lower().replace(" ", "_") + "_"
    func_name = f"{prefix}create_{_snake(obj_name)}"

    lines = []
    lines.append(f"def {func_name}({sig}):")
    lines.append(f'    """创建 {vba_obj}。')
    lines.append("")
    lines.append("    自动生成。参数说明：")
    for p in all_params:
        lines.append(f"    {p['name']}: {p.get('description', '')}")
    lines.append('    """')
    lines.append("")

    # 逐方法生成 VBA 行
    lines.append("    vba_lines = [")
    for m in block_methods:
        mname = m["name"]
        params = m.get("params", [])
        if not params:
            lines.append(f'        f"{vba_obj}.{mname}",')
            continue

        # 逐参数
        arg_parts = []
        for p in params:
            if p.get("hardcoded"):
                # 硬编码值在 f"..." 内用单引号避免冲突
                arg_parts.append(f"_q('{p['hardcoded']}')")
                continue
            pname = p["name"]
            ptype = p.get("type", "str")
            ref = _vba_ref(pname, ptype, enum_names)
            if _is_quoted(ptype, enum_names):
                arg_parts.append(f"_q({ref})")
            else:
                arg_parts.append(f"_v({ref})")
        # 每个 arg 独立的 f-string 表达式，逗号在表达式外
        args_expr = ", ".join(f"{{{p}}}" for p in arg_parts)
        lines.append(f'        f"{vba_obj}.{mname} {args_expr}",')

    lines.append("    ]")
    lines.append('    vba = "\\n".join(vba_lines)')

    label_var = all_params[0]["name"] if all_params else "obj"
    lines.append(f'    project.modeler.add_to_history(f"Define {vba_obj}:{{{label_var}}}", vba)')
    lines.append("")
    return lines


def gen_standalone_fn(method: dict, enums: dict) -> list[str]:
    mname = method["name"]
    func_name = _snake(mname)
    params = method.get("params", [])
    enum_names = set(enums.keys())
    sig = _build_sig(params, enum_names)

    lines = []
    lines.append(f"def {func_name}({sig}):")
    lines.append(f'    """{method.get("description", mname)}。"""')

    vba_raw = method.get("vba_raw", "")
    if vba_raw:
        lines.append(f"    vba = f'''{vba_raw}'''")
    else:
        # 自动生成
        arg_parts = []
        for p in params:
            pname = p["name"]
            ptype = p.get("type", "str")
            ref = _vba_ref(pname, ptype, enum_names)
            if _is_quoted(ptype, enum_names):
                arg_parts.append(f"_q({ref})")
            else:
                arg_parts.append(f"_v({ref})")
        args_expr = ", ".join(f"{{{p}}}" for p in arg_parts)
        lines.append(f'    vba = f"{mname} {args_expr}"')

    lines.append(f'    project.modeler.add_to_history("{mname}", vba)')
    lines.append("")
    return lines


def gen_registry(obj: dict, block_methods: list[dict], standalone_methods: list[dict], enums: dict) -> list[str]:
    obj_name = obj["name"]
    categories = obj.get("categories", [])

    entries = []

    # With block → create tool
    if block_methods:
        prefix = ""
        if categories:
            prefix = categories[0].lower().replace(" ", "_") + "_"
        tool = f"create-{_kebab(obj_name)}"
        fn = f"{prefix}create_{_snake(obj_name)}"
        desc = _build_params_desc(_collect_params(block_methods))
        entries.append(f"""    "{tool}": {{
        "fn": {fn},
        "params": {desc!r},
    }},""")

    # standalone tools
    for m in standalone_methods:
        if not m.get("standalone"):
            continue
        tool = _kebab(m["name"])
        fn = _snake(m["name"])
        desc = _build_params_desc(m.get("params", []))
        entries.append(f"""    "{tool}": {{
        "fn": {fn},
        "params": {desc!r},
    }},""")

    if not entries:
        return []

    return ["TOOLS_TO_REGISTER = {", *entries, "}", ""]


# ── 入口 ──────────────────────────────────────────────────


def generate_one(toml_path: Path) -> str | None:
    with open(toml_path, "r", encoding="utf-8") as f:
        data = tomllib.loads(f.read())

    obj = data.get("object", {})
    if not obj:
        print(f"  [跳过] {toml_path.name}: 缺少 [object]")
        return None

    enums = data.get("enums", {})
    all_methods = list(data.get("methods", []))

    # Split: block methods (before block_end) + rest
    # 无 block_end → 所有 standalone 方法，无 With 块
    block_methods = []
    standalone_methods = []
    found_block_end = False
    for m in all_methods:
        if m.pop("block_end", False):
            block_methods.append(m)
            found_block_end = True
            break
        block_methods.append(m)
    if found_block_end:
        standalone_methods = all_methods[len(block_methods):]
    else:
        standalone_methods = block_methods
        block_methods = []

    output: list[str] = [HEADER]
    output.extend(gen_enums(enums))
    if block_methods:
        output.extend(gen_block_fn(obj, block_methods, enums))
    for m in standalone_methods:
        if m.get("standalone"):
            output.extend(gen_standalone_fn(m, enums))
    output.extend(gen_registry(obj, block_methods, standalone_methods, enums))

    return "\n".join(output) + "\n"


def main() -> None:
    toml_files = sorted(DEFS_DIR.glob("*.toml"))
    if not toml_files:
        print(f"[错误] 无 TOML 文件: {DEFS_DIR}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for tf in toml_files:
        print(f"  {tf.name} → ", end="")
        code = generate_one(tf)
        if code is None:
            print("跳过")
            continue
        out_name = f"gen_{tf.stem}.py"
        out_path = OUTPUT_DIR / out_name
        out_path.write_text(code, encoding="utf-8")
        print(f"{out_name} ({len(code)} bytes)")


if __name__ == "__main__":
    main()
