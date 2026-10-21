"""`.aedt` 文本解析器：从 Twin Builder 工程文件发现 SimulinkData 元件与端口表。

对应设计 `docs/design/simulink-binding.md` §3（解析器设计）、§3.2（定位规则）、§3.4（边界）。
纯文本处理、无外部依赖，可脱机跑（设计 §5.1「本批唯一单测面」）。

`.aedt` 是 `$begin 'X'` / `$end 'X'` 的嵌套帧文本。本解析器只依赖三个实测事实：
1. 实例的元件描述在 `$begin 'Compinst'` 帧**及其嵌套子帧**内——目标字段实测在 `CompData` 子帧里，
   按「栈顶帧名 == Compinst」判等会零命中（设计 §3.2 第 3 步）；
2. design 归属走 `$begin 'Instance'` 段的 `DesignEditor` + `Refdes('<ID>', '<实例名>')`（设计 §3.1）；
3. 分析名在 `$begin 'DesignInfo'` 段的 `DesignName=` / `'Nominal Setups'[1: '<名>']`（设计 §3.1）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from data_exchange.models import BindingSpec, Port

FRAME_BEGIN = "$begin"
FRAME_END = "$end"

# `$begin 'Compinst'` / `$end 'Compinst'`
_FRAME_RE = re.compile(r"^\$(begin|end)\s+'([^']*)'\s*$")
_COMPINST = "Compinst"
_INSTANCE = "Instance"
_DESIGN_INFO = "DesignInfo"

# 叶子字段：`名=值` 或 `名='值'`
_KV_RE = re.compile(r"^([A-Za-z_]\w*)\s*=\s*(?:'((?:[^'\\]|\\.)*)'|(.*))$")
_REFDES_RE = re.compile(r"^Refdes\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)\s*$")
_SETUPS_RE = re.compile(r"^'Nominal Setups'\s*\[\d+\s*:\s*'([^']*)'\]\s*$")
_SIM_NAME_RE = re.compile(r"^SimulinkName(\d+)$")
_SIM_DIR_RE = re.compile(r"^SimulinkDirection(\d+)$")
# `TextProp('InstanceName', 'OD', '', CB='InstanceName', 'MDL1')` —— 实例名在最后一个参数
_TEXT_PROP_RE = re.compile(r"^TextProp\(\s*'([^']*)'\s*,.*?,\s*'((?:[^'\\]|\\.)*)'\s*\)\s*$")

_SIMULINK_DATA = "SimulinkData"


class ParseError(Exception):
    """解析阶段失败（对应退出码 2，设计 §6.2）。消息已是四段式（设计 §6.1）。"""


@dataclass
class _Compinst:
    """一个最外层 `Compinst` 帧：子树内收集到的键值对（同名键保留最先出现的一条）。"""

    line_no: int
    data: dict[str, str] = field(default_factory=dict)
    type_hit: str = ""  # 子树内首次出现的 ComponentDataType 值


@dataclass
class _Instance:
    """一个 `Instance` 段：design 名与 (元件ID, 实例名) 的登记表。"""

    line_no: int
    design_editor: str = ""
    refdes: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class _DesignInfo:
    """一个 `DesignInfo` 段：design 名与首个 analysis 名。"""

    line_no: int
    design_name: str = ""
    first_setup: str = ""


def _read_lines(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise ParseError(f"解析 | {path} | 路径存在且可读 | 路径不存在（{exc.strerror}）") from exc
    except OSError as exc:
        raise ParseError(f"解析 | {path} | 路径存在且可读 | 读取失败：{exc}") from exc
    return text.splitlines()


def _parse_kv(line: str) -> tuple[str, str] | None:
    m = _KV_RE.match(line)
    if not m:
        return None
    quoted, bare = m.group(2), m.group(3)
    if quoted is not None:
        return m.group(1), quoted.replace("\\\\", "\\")
    return m.group(1), bare.strip()


def _scan(lines: list[str]) -> tuple[list[_Compinst], list[_Instance], list[_DesignInfo]]:
    """一趟扫描分出三类帧。

    `Compinst` 用**子树判据**：进入帧后置标志，直到配对 `$end 'Compinst'` 之前，任一层级出现的
    叶子字段都收进同一个实例（设计 §3.2 第 3 步）。嵌套 `Compinst`（实测存在于 DataInstances 段）
    并入外层实例，不另起一个。
    """
    compinsts: list[_Compinst] = []
    instances: list[_Instance] = []
    designs: list[_DesignInfo] = []

    stack: list[str] = []
    open_comp: _Compinst | None = None
    open_inst: _Instance | None = None
    open_design: _DesignInfo | None = None

    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue

        m = _FRAME_RE.match(line)
        if m:
            kind, name = m.group(1), m.group(2)
            if kind == "begin":
                stack.append(name)
                if name == _COMPINST:
                    if open_comp is None:
                        open_comp = _Compinst(line_no=line_no)
                elif name == _INSTANCE:
                    if open_inst is None:
                        open_inst = _Instance(line_no=line_no)
                    else:
                        # 嵌套 Instance 段并入外层：Refdes 与 DesignEditor 取同一段内的
                        pass
                elif name == _DESIGN_INFO and open_design is None:
                    open_design = _DesignInfo(line_no=line_no)
                continue
            # $end
            if not stack:
                continue
            top = stack.pop()
            if top != name:
                # 帧不配对：以栈顶名义关闭，避免栈漂移
                name = top
            if name == _COMPINST and not any(n == _COMPINST for n in stack):
                if open_comp is not None:
                    compinsts.append(open_comp)
                    open_comp = None
            elif name == _INSTANCE and not any(n == _INSTANCE for n in stack):
                if open_inst is not None:
                    instances.append(open_inst)
                    open_inst = None
            elif name == _DESIGN_INFO and not any(n == _DESIGN_INFO for n in stack):  # noqa: SIM102 —— 拆开更易读
                if open_design is not None:
                    designs.append(open_design)
                    open_design = None
            continue

        if open_comp is not None:
            tp = _TEXT_PROP_RE.match(line)
            if tp:
                # TextProp 不是 `名=值` 形态，单独按实测形态取实例名（设计 §3.1：`:49791`）
                open_comp.data.setdefault(tp.group(1), tp.group(2))
            else:
                kv = _parse_kv(line)
                if kv is not None:
                    open_comp.data.setdefault(kv[0], kv[1])
                    if kv[0] == "ComponentDataType" and not open_comp.type_hit:
                        open_comp.type_hit = kv[1]
        if open_inst is not None:
            ref = _REFDES_RE.match(line)
            if ref:
                open_inst.refdes.append((ref.group(1), ref.group(2)))
                continue
            kv = _parse_kv(line)
            if kv is not None and kv[0] == "DesignEditor" and not open_inst.design_editor:
                open_inst.design_editor = kv[1]
        if open_design is not None:
            setups = _SETUPS_RE.match(line)
            if setups:
                if not open_design.first_setup:
                    open_design.first_setup = setups[1]
                continue
            kv = _parse_kv(line)
            if kv is not None and kv[0] == "DesignName" and not open_design.design_name:
                open_design.design_name = kv[1]

    return compinsts, instances, designs


def _ports_from(data: dict[str, str], where: str) -> list[Port]:
    """按序号拼端口：`SimulinkName<i>` / `SimulinkDirection<i>`（设计 §3.2 第 5 步）。"""
    names: dict[int, str] = {}
    dirs: dict[int, int] = {}
    for key, value in data.items():
        m = _SIM_NAME_RE.match(key)
        if m:
            names[int(m.group(1))] = value
            continue
        m = _SIM_DIR_RE.match(key)
        if m:
            try:
                dirs[int(m.group(1))] = int(value)
            except ValueError as exc:
                raise ParseError(
                    f"解析 | {where} 的 {key} | 方向是整数 | 读到 {value!r}"
                ) from exc
    size_raw = data.get("SimulinkVectorSize", "")
    try:
        size = int(size_raw) if size_raw else len(names)
    except ValueError as exc:
        raise ParseError(
            f"解析 | {where} 的 SimulinkVectorSize | 整数 | 读到 {size_raw!r}"
        ) from exc
    ports: list[Port] = []
    for i in range(size):
        if i not in names or i not in dirs:
            raise ParseError(
                f"解析 | {where} 第 {i} 个端口 | SimulinkName{i} 与 SimulinkDirection{i} 都在 | "
                f"名字{'有' if i in names else '缺'}、方向{'有' if i in dirs else '缺'}"
            )
        dir_value = dirs[i]
        if dir_value not in (0, 1):
            raise ParseError(
                f"解析 | {where} 第 {i} 个端口 | SimulinkDirection 取 0 或 1 | 读到 {dir_value}"
            )
        ports.append(Port(index=i, name=names[i], direction=dir_value))
    return ports


def _find_design(entry: _Compinst, instances: list[_Instance]) -> str:
    """design 归属：`Refdes('<ID>', '<实例名>')` 命中的 Instance 段的 `DesignEditor`（设计 §3.2 第 4 步）。"""
    comp_id = entry.data.get("ID", "")
    instance = entry.data.get("InstanceName", "")
    where = f".aedt:{entry.line_no} ID={comp_id or '?'} instance={instance or '?'}"
    hits = [inst.design_editor for inst in instances if (comp_id, instance) in inst.refdes]
    hits = [h for h in hits if h]
    if not hits:
        raise ParseError(
            f"解析 | {where} | 存在 Refdes('{comp_id}','{instance}') 且带 DesignEditor 的 Instance 段 | 0 段命中"
        )
    uniq = sorted(set(hits))
    if len(uniq) > 1:
        raise ParseError(
            f"解析 | {where} | design 归属唯一 | 多段命中且不一致：{uniq}"
        )
    return uniq[0]


def parse_aedt(path: str | Path) -> list[BindingSpec]:
    """解析 `.aedt`，返回全部 SimulinkData 元件的绑定清单（按文件出现顺序）。

    失败一律抛 `ParseError`（消息四段式），由入口脚本映射为退出码 2。
    0 个元件也算解析失败（设计 §3.4）。
    """
    aedt = Path(path).expanduser()
    if not aedt.is_absolute():
        aedt = aedt.resolve()
    lines = _read_lines(aedt)

    compinsts, instances, designs = _scan(lines)
    design_info = {d.design_name: d for d in designs if d.design_name}

    specs: list[BindingSpec] = []
    seen_blk: set[str] = set()

    for entry in compinsts:
        # 第 3 步：子树判据——Compinst 帧及其全部嵌套子帧里出现该字段即命中
        if entry.type_hit != _SIMULINK_DATA:
            continue

        comp_name = entry.data.get("CompName", "")
        comp_id = entry.data.get("ID", "")
        instance = entry.data.get("InstanceName", "")
        where = f".aedt:{entry.line_no} CompName={comp_name} ID={comp_id}"
        if not instance:
            raise ParseError(
                f"解析 | {where} | 有 TextProp('InstanceName', ...) 行 | 未找到"
            )

        design = _find_design(entry, instances)
        info = design_info.get(design)
        if info is None:
            raise ParseError(
                f"解析 | {where} design={design} | 有同名 DesignInfo 段 | 未找到"
            )
        analysis = info.first_setup
        if not analysis:
            raise ParseError(
                f"解析 | .aedt:{info.line_no} design={design} | 'Nominal Setups'[1: '<名>'] 有名 | 读到空"
            )

        ports = _ports_from(entry.data, where)

        blk = instance
        if blk in seen_blk:
            n = 2
            while f"{instance}_{n}" in seen_blk:
                n += 1
            blk = f"{instance}_{n}"
        seen_blk.add(blk)

        specs.append(
            BindingSpec(
                aedt_path=aedt,
                project=aedt.stem,
                design=design,
                analysis=analysis,
                comp_name=comp_name,
                instance=instance,
                vector_size=len(ports),
                ports=ports,
                comp_id=comp_id,
                block=blk,
            )
        )

    if not specs:
        raise ParseError(
            f"解析 | {aedt} | 至少 1 个 ComponentDataType='SimulinkData' 的元件 | "
            f"扫描 {len(lines)} 行，Compinst 帧 {len(compinsts)} 个，命中 0 个"
        )
    return specs
