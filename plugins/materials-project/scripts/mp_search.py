#!/usr/bin/env python3
"""Materials Project 数据库搜索。

用法示例：
  uv run scripts/mp_search.py --formula TiO2
  uv run scripts/mp_search.py --elements Li Fe O --stable --band-gap 0.5 2.0
  uv run scripts/mp_search.py --chemsys Li-Fe-O --eabovehull 0.025 --limit 50
  uv run scripts/mp_search.py --ids mp-149 mp-4163
  uv run scripts/mp_search.py --formula Fe2O3 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _mp_common import handle_api_error, make_rester, fmt_num  # noqa: E402

DEFAULT_FIELDS = [
    "material_id", "formula_pretty", "symmetry",
    "band_gap", "energy_above_hull", "is_stable", "density", "volume",
]
FIELD_LABELS = {
    "material_id": "material_id",
    "formula_pretty": "化学式",
    "symmetry": "空间群",
    "crystal_system": "晶系",
    "band_gap": "带隙 (eV)",
    "energy_above_hull": "E_hull (eV/atom)",
    "is_stable": "稳定",
    "density": "密度 (g/cm³)",
    "volume": "体积 (Å³)",
}


def symmetry_attr(sym, name):
    """从 symmetry 字段（pydantic 对象或 dict）提取子属性。"""
    if sym is None:
        return None
    if isinstance(sym, dict):
        return sym.get(name)
    return getattr(sym, name, None)


def parse_args():
    p = argparse.ArgumentParser(description="Materials Project 数据库搜索")
    q = p.add_mutually_exclusive_group(required=True)
    q.add_argument("--formula", help="化学式，如 TiO2（支持通配符 *）")
    q.add_argument("--elements", nargs="+", metavar="EL", help="元素列表，如 Li Fe O")
    q.add_argument("--chemsys", help="化学体系，如 Li-Fe-O")
    q.add_argument("--ids", nargs="+", metavar="ID", help="material_id 列表，如 mp-149")
    p.add_argument("--band-gap", nargs=2, type=float, metavar=("MIN", "MAX"),
                   help="带隙范围 (eV)")
    p.add_argument("--stable", action="store_true", help="仅热力学稳定相")
    p.add_argument("--eabovehull", type=float, metavar="MAX",
                   help="E_above_hull 上限 (eV/atom)")
    p.add_argument("--crystal-system", dest="crystal_system",
                   choices=["triclinic", "monoclinic", "orthorhombic", "tetragonal",
                            "trigonal", "hexagonal", "cubic"], help="晶系过滤")
    p.add_argument("--spacegroup", help="空间群符号，如 Fm-3m")
    p.add_argument("--num-elements", nargs=2, type=int, metavar=("MIN", "MAX"),
                   help="元素数目范围")
    p.add_argument("--fields", help="返回字段（逗号分隔），默认输出常用字段")
    p.add_argument("--limit", type=int, default=20, help="最多返回条数（默认 20）")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return p.parse_args()


def build_kwargs(args):
    kw = {"num_chunks": 1, "chunk_size": args.limit}
    if args.formula:
        kw["formula"] = args.formula
    elif args.elements:
        kw["elements"] = [e.strip().capitalize() for e in args.elements]
    elif args.chemsys:
        kw["chemsys"] = args.chemsys
    elif args.ids:
        kw["material_ids"] = args.ids
    if args.band_gap:
        kw["band_gap"] = tuple(args.band_gap)
    if args.stable:
        kw["is_stable"] = True
    if args.eabovehull is not None:
        kw["energy_above_hull"] = (0, args.eabovehull)
    if args.crystal_system:
        kw["crystal_system"] = args.crystal_system
    if args.spacegroup:
        kw["spacegroup_symbol"] = args.spacegroup
    if args.num_elements:
        kw["nelements"] = tuple(args.num_elements)
    return kw


def doc_get(doc, field):
    try:
        v = getattr(doc, field, None)
        if v is None and isinstance(doc, dict):
            v = doc.get(field)
        return v
    except Exception:
        return None


def render_markdown(docs, fields):
    labels = [FIELD_LABELS.get(f, f) for f in fields]
    lines = [f"共 {len(docs)} 条结果（按 E_hull 升序）", "",
             "| " + " | ".join(labels) + " |",
             "|" + "---|" * len(fields)]
    for d in docs:
        row = []
        for f in fields:
            if f == "symmetry":
                v = symmetry_attr(doc_get(d, "symmetry"), "symbol")
            elif f == "crystal_system":
                v = symmetry_attr(doc_get(d, "symmetry"), "crystal_system")
            else:
                v = doc_get(d, f)
            if f in ("band_gap", "energy_above_hull", "density", "volume"):
                row.append(fmt_num(v))
            elif f == "is_stable":
                row.append("✓" if v else "✗")
            else:
                row.append(str(v) if v is not None else "—")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append("注：E_hull = energy_above_hull，≤ 0.025 eV/atom 通常视为可合成候选；"
                 "带隙为 GGA/PBE 值，普遍低估实际带隙。")
    return "\n".join(lines)


def to_jsonable(doc):
    if isinstance(doc, dict):
        return doc
    if hasattr(doc, "model_dump"):
        return doc.model_dump(mode="json")
    return {f: doc_get(doc, f) for f in DEFAULT_FIELDS}


def main():
    args = parse_args()
    kw = build_kwargs(args)
    fields = ([f.strip() for f in args.fields.split(",")] if args.fields else DEFAULT_FIELDS)
    try:
        with make_rester() as mpr:
            docs = mpr.materials.summary.search(fields=fields, **kw)
    except Exception as exc:  # noqa: BLE001
        handle_api_error(exc)

    docs = sorted(docs, key=lambda d: doc_get(d, "energy_above_hull") or 0.0)[: args.limit]
    if args.json:
        print(json.dumps([to_jsonable(d) for d in docs], ensure_ascii=False, indent=2, default=str))
    elif not docs:
        print("未找到匹配条目。可尝试放宽过滤条件（如去掉 --stable / --band-gap）。")
    else:
        print(render_markdown(docs, fields))


if __name__ == "__main__":
    main()
