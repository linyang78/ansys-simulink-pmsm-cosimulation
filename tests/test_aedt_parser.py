"""`.aedt` 解析器单测（本批唯一单测面，设计 §5.1）。

对应设计 §3（解析器设计）、§3.2 第 3 步（子树判据）、§3.4（边界）、
§4.3（UserData 构造与索引）、§6.3（F1）。纯文本、可脱机跑，不启动 MATLAB。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from data_exchange.aedt_parser import ParseError, parse_aedt

SAMPLE = PROJECT_ROOT / "models" / "manual" / "RotorySimulink_thincoder.aedt"

_HEAD = "\t$begin 'ProjectPreview'"


def _compinst(
    comp_id: str,
    instance: str,
    comp_name: str = "SimulinkData10",
    nested: bool = True,
    ports: list[tuple[str, int]] | None = None,
) -> str:
    """造一个 Compinst 帧；`nested=True` 时目标字段放在 CompData 子帧里（实测形态）。"""
    ports = ports if ports is not None else [("u1", 1), ("i1", 0)]
    lines = [
        "\t\t\t$begin 'Compinst'",
        f"\t\t\t\tID='{comp_id}'",
        f"\t\t\t\tCompName='{comp_name}'",
        "\t\t\t\t$begin 'Parameters'",
        f"\t\t\t\t\tTextProp('InstanceName', 'OD', '', CB='InstanceName', '{instance}')",
        "\t\t\t\t$end 'Parameters'",
    ]
    pad = "\t\t\t\t\t"
    if nested:
        lines.append("\t\t\t\t$begin 'CompData'")
    lines.append(f"{pad}ComponentDataType='SimulinkData'")
    lines.append(f"{pad}SimulinkModelName='SimulinkData1'")
    lines.append(f"{pad}SimulinkVectorSize={len(ports)}")
    for i, (name, direction) in enumerate(ports):
        lines.append(f"{pad}SimulinkName{i}='{name}'")
        lines.append(f"{pad}SimulinkDirection{i}={direction}")
    if nested:
        lines.append("\t\t\t\t$end 'CompData'")
    lines.append("\t\t\t$end 'Compinst'")
    return "\n".join(lines)


def _instance(design: str, refdes: list[tuple[str, str]]) -> str:
    lines = ["\t\t$begin 'Instance'", f"\t\t\tDesignEditor='{design}'", "\t\t\tID='181'"]
    lines += [f"\t\t\tRefdes('{rid}', '{name}')" for rid, name in refdes]
    lines.append("\t\t$end 'Instance'")
    return "\n".join(lines)


def _design_info(design: str, setup: str) -> str:
    return "\n".join(
        [
            "\t$begin 'DesignInfo'",
            f"\t\tDesignName='{design}'",
            f"\t\t'Nominal Setups'[1: '{setup}']",
            "\t$end 'DesignInfo'",
        ]
    )


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "case.aedt"
    path.write_text(_HEAD + "\n" + body + "\n\t$end 'ProjectPreview'\n", encoding="utf-8")
    return path


# ---- 用例 1：实测样本的三套元件（F1 判据） --------------------------------


def test_parse_real_sample_three_components() -> None:
    """实测样本：3 个元件，design / 实例名 / 端口方向与名字逐一对应（F1 验收读数）。"""
    specs = parse_aedt(SAMPLE)
    assert len(specs) == 3

    got = [
        (s.comp_name, s.design, s.instance, s.block_name, [p.name for p in s.out_ports], [p.name for p in s.in_ports])
        for s in specs
    ]
    assert got == [
        ("SimulinkData10", "MatlabConnect", "MDL1", "MDL1", ["iA", "iB", "iC", "wm", "THM", "Te"], ["uA", "uB", "uC", "TL"]),
        ("SimulinkData2", "Simplorer1", "MDL1", "MDL1_2", ["i1", "i2", "i3"], ["u1", "u2", "u3"]),
        ("Simulink_Control", "Simplorer2", "MDL1", "MDL1_3", ["y1"], ["x1", "x2"]),
    ]
    assert all(s.analysis == "TR" for s in specs)
    assert all(s.project == "RotorySimulink_thincoder" for s in specs)
    assert all(s.aedt_path.is_absolute() for s in specs)


def test_real_sample_indices() -> None:
    """三套索引 = range(dir0) + range(dir1)（设计 §4.3，三套均实测过）。"""
    specs = parse_aedt(SAMPLE)
    assert [s.indices() for s in specs] == [
        [0, 1, 2, 3, 4, 5, 0, 1, 2, 3],
        [0, 1, 2, 0, 1, 2],
        [0, 0, 1],
    ]


def test_real_sample_userdata_matches_manual_link() -> None:
    """第一个元件的 UserData 与用户手工点 Link 的结果逐字节一致（设计 §4.3 对照基准）。"""
    spec = parse_aedt(SAMPLE)[0]
    expected = (
        "DataVer:2,E:\\Vscode\\thincoder-pmsm\\models\\manual\\RotorySimulink_thincoder.aedt,"
        "RotorySimulink_thincoder,MatlabConnect,TR,MDL1,6,4,iA,iB,iC,wm,THM,Te,uA,uB,uC,TL,0,1,2,3,4,5,0,1,2,3"
    )
    assert spec.build_userdata() == expected


def test_block_name_keeps_instance_in_userdata() -> None:
    """块名去重，UserData 实例名保持 .aedt 原文（用户裁决 2026-10-20）。"""
    specs = parse_aedt(SAMPLE)
    assert [s.block_name for s in specs] == ["MDL1", "MDL1_2", "MDL1_3"]
    assert [s.instance for s in specs] == ["MDL1", "MDL1", "MDL1"]
    for spec in specs:
        fields = spec.build_userdata().split(",")
        assert fields[5] == "MDL1"


# ---- 用例 2：0 个 SimulinkData 元件 --------------------------------------


def test_no_simulinkdata_component(tmp_path: Path) -> None:
    """设计 §3.4：0 个元件 ⇒ 解析失败（ParseError，退出码 2 的来源）。"""
    body = "\t\t\t$begin 'Compinst'\n\t\t\t\tID='1'\n\t\t\t\tCompName='E1'\n\t\t\t\t$begin 'CompData'\n\t\t\t\t\tComponentDataType='MaxwellECEData'\n\t\t\t\t$end 'CompData'\n\t\t\t$end 'Compinst'"
    with pytest.raises(ParseError) as ei:
        parse_aedt(_write(tmp_path, body))
    assert "解析" in str(ei.value)
    assert "SimulinkData" in str(ei.value)


# ---- 用例 3：子树判据（评审 #4 的守门用例） -------------------------------


def test_subtree_criterion_nested_compdata(tmp_path: Path) -> None:
    """ComponentDataType 在 Compinst → CompData 第 2 层内也必须命中（设计 §3.2 第 3 步）。"""
    body = "\n".join(
        [
            _compinst("206", "MDL1", nested=True),
            _instance("MatlabConnect", [("206", "MDL1")]),
            _design_info("MatlabConnect", "TR"),
        ]
    )
    specs = parse_aedt(_write(tmp_path, body))
    assert len(specs) == 1
    assert specs[0].block_name == "MDL1"
    # 端口行同样在子帧内，也要取到
    assert [p.name for p in specs[0].ports] == ["u1", "i1"]


def test_flat_compinst_also_hit(tmp_path: Path) -> None:
    """目标字段直接放在 Compinst 帧里（无 CompData 子帧）同样命中——判据是子树，不是某一层。"""
    body = "\n".join(
        [
            _compinst("206", "MDL1", nested=False),
            _instance("MatlabConnect", [("206", "MDL1")]),
            _design_info("MatlabConnect", "TR"),
        ]
    )
    assert len(parse_aedt(_write(tmp_path, body))) == 1


# ---- 用例 4：dir 计数与方向 ---------------------------------------------


def test_direction_count(tmp_path: Path) -> None:
    """dir0 / dir1 的计数与名字分开取；索引先 dir0 后 dir1（设计 §4.3）。"""
    ports = [("a", 1), ("b", 1), ("c", 0), ("d", 0), ("e", 0)]
    body = "\n".join(
        [
            _compinst("206", "MDL1", ports=ports),
            _instance("MatlabConnect", [("206", "MDL1")]),
            _design_info("MatlabConnect", "TR"),
        ]
    )
    spec = parse_aedt(_write(tmp_path, body))[0]
    assert [p.name for p in spec.out_ports] == ["c", "d", "e"]
    assert [p.name for p in spec.in_ports] == ["a", "b"]
    assert spec.indices() == [0, 1, 2, 0, 1]
    # 名字段先 dir0 后 dir1（实测字段序）：DataVer / 路径 / project / design / analysis / instance / dir0 数 / dir1 数 之后
    assert spec.build_userdata().split(",")[8:] == ["c", "d", "e", "a", "b", "0", "1", "2", "0", "1"]


# ---- 用例 5：边界与失败 ------------------------------------------------


def test_multiple_same_instance_block_names(tmp_path: Path) -> None:
    """同名实例块名追加 _2、_3（设计 §3.4），实例名保持原文。"""
    body = "\n".join(
        [
            _compinst("206", "MDL1", comp_name="SimulinkData10"),
            _compinst("207", "MDL1", comp_name="SimulinkData11"),
            _instance("MatlabConnect", [("206", "MDL1"), ("207", "MDL1")]),
            _design_info("MatlabConnect", "TR"),
        ]
    )
    specs = parse_aedt(_write(tmp_path, body))
    assert [s.block_name for s in specs] == ["MDL1", "MDL1_2"]
    assert [s.instance for s in specs] == ["MDL1", "MDL1"]


def test_missing_refdes_reports_id(tmp_path: Path) -> None:
    """找不到 design 归属（无匹配 Refdes）⇒ ParseError 且点名 ID（设计 §3.4 边界）。"""
    body = "\n".join(
        [
            _compinst("999", "MDL9"),
            _instance("MatlabConnect", [("206", "MDL1")]),
            _design_info("MatlabConnect", "TR"),
        ]
    )
    with pytest.raises(ParseError) as ei:
        parse_aedt(_write(tmp_path, body))
    assert "999" in str(ei.value)


def test_missing_file() -> None:
    """路径不存在 ⇒ ParseError 含「解析」与「路径不存在」（F4-a）。"""
    with pytest.raises(ParseError) as ei:
        parse_aedt(PROJECT_ROOT / "models" / "manual" / "_not_exist.aedt")
    msg = str(ei.value)
    assert "解析" in msg
    assert "路径不存在" in msg
