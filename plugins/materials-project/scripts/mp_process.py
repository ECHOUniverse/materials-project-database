#!/usr/bin/env python3
"""晶体结构处理：信息提取、对称性分析、单胞转换、超胞、XRD、格式转换。

输入为本地结构文件（cif/poscar/vasp/json 等按扩展名自动识别）或 --from-mp mp-149。
原始文件只读不修改；派生结构写入新文件（可用 -o 指定）。

用法示例：
  uv run scripts/mp_process.py POSCAR --info
  uv run scripts/mp_process.py mp-149.cif --symmetry
  uv run scripts/mp_process.py structure.cif --supercell 2 2 1 --convert poscar -o super.vasp
  uv run scripts/mp_process.py --from-mp mp-149 --xrd
  uv run scripts/mp_process.py mp-149.cif --primitive --convert cif -o prim.cif
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _mp_common import handle_api_error, make_rester, structure_info_md  # noqa: E402

SUPPORTED_OPS = ["--info", "--symmetry", "--primitive", "--conventional",
                 "--supercell", "--xrd", "--convert"]


def parse_args():
    p = argparse.ArgumentParser(description="晶体结构处理（pymatgen）")
    p.add_argument("file", nargs="?", help="输入结构文件（cif/poscar/vasp/json）")
    p.add_argument("--from-mp", metavar="MPID", help="从 Materials Project 读取结构，如 mp-149")
    p.add_argument("--info", action="store_true", help="结构摘要（成分/晶格/体积/密度）")
    p.add_argument("--symmetry", action="store_true", help="空间群对称性分析")
    p.add_argument("--primitive", action="store_true", help="转换为原胞")
    p.add_argument("--conventional", action="store_true", help="转换为惯用单胞")
    p.add_argument("--supercell", nargs=3, type=int, metavar=("A", "B", "C"), help="超胞倍数")
    p.add_argument("--xrd", action="store_true", help="粉末 XRD 模拟（2θ-强度表）")
    p.add_argument("--wavelength", default="CuKa", help="X 射线波长（默认 CuKa，可为浮点 Å）")
    p.add_argument("--convert", metavar="FMT", help="导出格式：cif/poscar/json/xyz")
    p.add_argument("-o", "--output", metavar="FILE", help="导出文件路径（默认 <原名>-<操作>.<ext>）")
    p.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = p.parse_args()
    if not args.file and not args.from_mp:
        p.error("需要提供输入结构文件，或使用 --from-mp mp-xxxx")
    ops_used = [op for op in (args.info, args.symmetry, args.primitive,
                              args.conventional, args.supercell, args.xrd, args.convert)]
    if not any(ops_used):
        p.error("未指定操作。可选：" + ", ".join(SUPPORTED_OPS))
    return args


def load_structure(args):
    """加载结构，返回 (structure, source_id, base_name)。"""
    if args.from_mp:
        mpid = args.from_mp.strip()
        try:
            with make_rester() as mpr:
                st = mpr.get_structure_by_material_id(mpid)
        except Exception as exc:  # noqa: BLE001
            handle_api_error(exc)
        return st, mpid, mpid
    path = Path(args.file)
    if not path.is_file():
        print(f"错误：文件不存在：{path}", file=sys.stderr)
        sys.exit(1)
    from pymatgen.core import Structure
    try:
        st = Structure.from_file(str(path))  # cif/poscar/vasp/json 均按扩展名自动识别
    except Exception as exc:  # noqa: BLE001
        print(f"错误：无法解析结构文件 {path}：{exc}", file=sys.stderr)
        sys.exit(1)
    return st, None, path.stem


def default_output_path(base, op_tag, fmt):
    ext = {"cif": ".cif", "poscar": ".vasp", "json": ".json", "xyz": ".xyz"}.get(fmt, f".{fmt}")
    return f"{base}-{op_tag}{ext}"


def fmt_wavelength(w):
    try:
        return float(w)
    except ValueError:
        return w  # pymatgen 接受 "CuKa" 等命名波长


def main():
    args = parse_args()
    structure, source_id, base = load_structure(args)
    current = structure
    md_parts = []
    json_payload = {}
    op_tags = []

    if source_id:
        json_payload["source_material_id"] = source_id

    if args.info:
        md_parts.append(structure_info_md(current, title="结构信息"))
        json_payload["info"] = {
            "formula": current.composition.reduced_formula,
            "nsites": len(current),
            "volume_A3": round(current.volume, 4),
            "density_g_cm3": round(current.density, 4),
            "lattice_abc": [round(v, 4) for v in current.lattice.abc],
            "lattice_angles": [round(v, 2) for v in current.lattice.angles],
        }

    if args.symmetry:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        sga = SpacegroupAnalyzer(current, symprec=0.01)
        info = {
            "spacegroup_symbol": sga.get_space_group_symbol(),
            "spacegroup_number": sga.get_space_group_number(),
            "crystal_system": sga.get_crystal_system(),
            "point_group": sga.get_point_group_symbol(),
        }
        md_parts.append(
            "## 对称性分析\n\n"
            f"- 空间群：**{info['spacegroup_symbol']}**（国际编号 {info['spacegroup_number']}）\n"
            f"- 晶系：{info['crystal_system']}\n"
            f"- 点群：{info['point_group']}")
        json_payload["symmetry"] = info
        op_tags.append("symmetry")

    if args.primitive or args.conventional:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        sga = SpacegroupAnalyzer(current, symprec=0.01)
        current = sga.get_primitive_standard_structure() if args.primitive \
            else sga.get_conventional_standard_structure()
        tag = "primitive" if args.primitive else "conventional"
        md_parts.append(structure_info_md(current, title=f"{tag} 单胞"))
        op_tags.append(tag)

    if args.supercell:
        current = current.copy()
        current.make_supercell(args.supercell)
        tag = "supercell-{}x{}x{}".format(*args.supercell)
        md_parts.append(structure_info_md(current, title=f"超胞 {args.supercell}"))
        op_tags.append(tag)

    if args.xrd:
        from pymatgen.analysis.diffraction.xrd import XRDCalculator
        calc = XRDCalculator(wavelength=fmt_wavelength(args.wavelength))
        pattern = calc.get_pattern(current)
        rows = []
        for two_theta, intensity, hkls in zip(pattern.x, pattern.y, pattern.hkls):
            hkl_str = ",".join(str(h["hkl"]) for h in hkls[:2])
            rows.append((two_theta, intensity, hkl_str))
        md_parts.append(
            f"## 粉末 XRD 模拟（波长 {args.wavelength}）\n\n"
            "| 2θ (°) | 相对强度 | (hkl) |\n|---|---|---|\n" +
            "\n".join(f"| {t:.2f} | {i:.1f} | {h} |" for t, i, h in rows[:30]))
        json_payload["xrd"] = {
            "wavelength": str(args.wavelength),
            "peaks": [{"two_theta_deg": round(t, 4), "relative_intensity": round(i, 2),
                       "hkl": h} for t, i, h in rows],
        }
        op_tags.append("xrd")

    if args.json:
        print(json.dumps(json_payload, ensure_ascii=False, indent=2))
    else:
        print("\n\n".join(md_parts))

    if args.convert:
        fmt = args.convert.strip().lower()
        if fmt not in ("cif", "poscar", "json", "xyz"):
            print(f"错误：不支持的导出格式 {fmt}（支持 cif/poscar/json/xyz）", file=sys.stderr)
            sys.exit(1)
        out = Path(args.output) if args.output else Path(default_output_path(base, "-".join(op_tags), fmt))
        if fmt == "poscar" and not out.suffix:
            out = out.with_suffix(".vasp")
        current.to(filename=str(out), fmt=fmt)
        print(f"\n已导出派生结构：{out}（原始文件未修改）", file=sys.stderr)
        if source_id:
            print(f"来源 entry：{source_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
