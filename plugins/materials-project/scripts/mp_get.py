#!/usr/bin/env python3
"""获取 Materials Project 材料详情与格式化晶体信息，支持多格式导出。

用法示例：
  uv run scripts/mp_get.py mp-149                      # 材料摘要
  uv run scripts/mp_get.py mp-149 --structure          # 摘要 + 晶体结构详情
  uv run scripts/mp_get.py mp-149 --conventional --save cif,poscar
  uv run scripts/mp_get.py mp-4163 --primitive --save cif --outdir structures
  uv run scripts/mp_get.py mp-149 --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _mp_common import (  # noqa: E402
    fmt_num, handle_api_error, make_rester, structure_info_md,
)

SUMMARY_FIELDS = [
    "material_id", "formula_pretty", "formula_anonymous", "symmetry",
    "density", "volume", "nsites", "nelements",
    "band_gap", "is_stable", "energy_above_hull", "formation_energy_per_atom",
    "uncorrected_energy_per_atom", "ordering", "is_magnetic",
    "total_magnetization", "theoretical",
]


def parse_args():
    p = argparse.ArgumentParser(description="获取 MP 材料详情与晶体结构")
    p.add_argument("material_id", help="material_id，如 mp-149")
    p.add_argument("--structure", action="store_true", help="附带晶体结构详情（晶格+坐标）")
    p.add_argument("--conventional", action="store_true", help="使用惯用单胞")
    p.add_argument("--primitive", action="store_true", help="使用原胞")
    p.add_argument("--initial", action="store_true", help="取弛豫前初始结构")
    p.add_argument("--save", help="导出格式，逗号分隔：cif,poscar,json（可组合）")
    p.add_argument("--outdir", default=".", help="导出目录（默认当前目录）")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return p.parse_args()


def fetch(mpid, cell_args):
    """返回 (summary_dict, structure)。"""
    cell_kw = {}
    if cell_args.primitive:
        cell_kw["conventional_unit_cell"] = False
    elif cell_args.conventional:
        cell_kw["conventional_unit_cell"] = True
    with make_rester() as mpr:
        docs = mpr.materials.summary.search(
            material_ids=[mpid], fields=SUMMARY_FIELDS, num_chunks=1, chunk_size=1)
        if not docs:
            print(f"错误：未找到 {mpid}。请确认 material_id 是否正确（可先用 mp_search.py 查找）。",
                  file=sys.stderr)
            sys.exit(1)
        doc = docs[0]
        summary = doc.model_dump(mode="json") if hasattr(doc, "model_dump") else dict(doc)
        structure = mpr.get_structure_by_material_id(
            mpid, final=not cell_args.initial, **cell_kw)
        if isinstance(structure, list):  # final=False 可能返回多个初始结构，取最后一个
            structure = structure[-1]
    return summary, structure


def render_md(summary, structure, mpid, want_structure, cell_tag):
    sym = summary.get("symmetry") or {}
    if not isinstance(sym, dict):
        sym = sym.model_dump(mode="json") if hasattr(sym, "model_dump") else {}
    lines = [f"# {summary.get('formula_pretty', mpid)}（{mpid}）", ""]
    rows = [
        ("化学式（约简）", summary.get("formula_pretty")),
        ("化学式（匿名）", summary.get("formula_anonymous")),
        ("空间群", f"{sym.get('symbol', '—')} (No.{sym.get('number', '—')})"),
        ("晶系", sym.get("crystal_system")),
        ("原子数 / 元素数", f"{summary.get('nsites', '—')} / {summary.get('nelements', '—')}"),
        ("体积 (Å³)", fmt_num(summary.get("volume"))),
        ("密度 (g/cm³)", fmt_num(summary.get("density"))),
        ("带隙 (eV, GGA)", fmt_num(summary.get("band_gap"))),
        ("形成能 (eV/atom)", fmt_num(summary.get("formation_energy_per_atom"))),
        ("E_above_hull (eV/atom)", fmt_num(summary.get("energy_above_hull"))),
        ("热力学稳定", "✓" if summary.get("is_stable") else "✗"),
        ("磁性序", summary.get("ordering") or "—"),
        ("理论计算数据", "是" if summary.get("theoretical") else "否"),
    ]
    lines.append("| 属性 | 值 |")
    lines.append("|---|---|")
    lines += [f"| {k} | {v if v is not None else '—'} |" for k, v in rows]
    lines.append("")
    lines.append("注：带隙为 GGA/PBE 值，普遍低估；E_hull ≤ 0.025 eV/atom 通常视为可合成候选。")
    if want_structure:
        lines.append("")
        lines.append(structure_info_md(structure, title=f"晶体结构信息（{cell_tag}）"))
    return "\n".join(lines)


def export(structure, mpid, save, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for fmt in [s.strip().lower() for s in save.split(",") if s.strip()]:
        if fmt == "cif":
            f = out / f"{mpid}.cif"
            structure.to(filename=str(f), fmt="cif")
        elif fmt in ("poscar", "vasp"):
            f = out / f"POSCAR-{mpid}"
            structure.to(filename=str(f), fmt="poscar")
        elif fmt == "json":
            f = out / f"{mpid}.json"
            structure.to(filename=str(f), fmt="json")
        else:
            print(f"警告：不支持的导出格式 {fmt}（支持 cif/poscar/json），已跳过。", file=sys.stderr)
            continue
        saved.append(str(f))
    if saved:
        print("已导出：", file=sys.stderr)
        for f in saved:
            print(f"  {f}", file=sys.stderr)


def main():
    args = parse_args()
    if args.primitive and args.conventional:
        print("错误：--primitive 与 --conventional 互斥，只能选一个。", file=sys.stderr)
        sys.exit(1)
    cell_tag = ("原胞" if args.primitive else "惯用单胞") if (args.primitive or args.conventional) \
        else "MP 收录的弛豫结构"
    mpid = args.material_id.strip()
    try:
        summary, structure = fetch(mpid, args)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        handle_api_error(exc)

    if args.json:
        payload = {"summary": summary,
                   "structure": json.loads(structure.to_json()) if args.structure else None}
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(render_md(summary, structure, mpid, args.structure, cell_tag))
    if args.save:
        export(structure, mpid, args.save, args.outdir)


if __name__ == "__main__":
    main()
