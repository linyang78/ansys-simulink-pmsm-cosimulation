"""跨工具数据对象：绑定清单、绑定结果、UserData 构造。

对应设计 `docs/design/simulink-binding.md` §3.3（数据结构）、§4.3（UserData 构造与判据）、§6.1（错误信息四段式）。
段与段之间只传这里的对象，不共享句柄——任一段可单独跑测试（设计 §2.1）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# 绑定阶段（设计 §4.1 单块动作序列的步骤名，失败信息「阶段」段的取值）
STAGE_PARSE = "解析"
STAGE_ADD_BLOCK = "建块"
STAGE_TRIGGER = "触发弹窗"
STAGE_DIALOG = "操作弹窗"
STAGE_BROWSE = "选择文件"
STAGE_CLOSE = "关窗"
STAGE_WRITE = "写回"
STAGE_SAVE = "保存"
STAGE_VERIFY = "核验"
STAGE_ENGINE = "引擎"

USERDATA_PREFIX = "DataVer:2,"


@dataclass(frozen=True)
class Port:
    """一个 SimulinkData 端口。

    direction 语义（实测）：1 = 输入到 Twin Builder（来自 Simulink），0 = 输出到 Simulink。
    契约依据：设计 §3.3。
    """

    index: int
    name: str
    direction: int


@dataclass(frozen=True)
class BindingSpec:
    """一个待绑定元件的全部期望值；核验阶段逐字段比对的就是这些值。

    契约依据：设计 §3.3。`ports` 按 .aedt 中的序号（`SimulinkName<i>` / `SimulinkDirection<i>`）排列。
    """

    aedt_path: Path  # .aedt 绝对路径
    project: str  # .aedt 文件名去扩展名
    design: str  # DesignEditor 名
    analysis: str  # Nominal Setups 首项（本批实样为 TR）
    comp_name: str  # 例：SimulinkData10（定位元件用 CompName，不用 SimulinkModelName）
    instance: str  # .aedt 原文实例名，例 MDL1；写进 UserData，必须忠于原文
    vector_size: int
    ports: list[Port] = field(default_factory=list)
    comp_id: str = ""  # .aedt Compinst 的 ID，失败信息里用于定位
    block: str = ""  # Simulink 块名：实例名重名时追加 _2、_3（设计 §3.4）

    @property
    def block_name(self) -> str:
        """Simulink 块名 = `block`（去重后），与 UserData 里的实例名 `instance` 是两回事。

        用户裁决 2026-10-20：`add_block` 拒绝重名，故块名必须去重（MDL1 / MDL1_2 / MDL1_3）；
        而 UserData 的实例名是 Twin Builder 回查 `.aedt` 的引用，必须保持 `.aedt` 原文的 MDL1。
        写成去重名会让 Twin Builder 在 `.aedt` 里找不到元件，绑定失效。
        """
        return self.block or self.instance

    @property
    def out_ports(self) -> list[Port]:
        """方向 0 的端口（Twin Builder 输出、送往 Simulink），UserData 名字段的后半段。"""
        return [p for p in self.ports if p.direction == 0]

    @property
    def in_ports(self) -> list[Port]:
        """方向 1 的端口（来自 Simulink、输入到 Twin Builder），UserData 名字段的前半段。"""
        return [p for p in self.ports if p.direction == 1]

    def indices(self) -> list[int]:
        """UserData 末尾的端口配对索引（设计 §4.3）。

        规则 = `range(dir0 端口数) + range(dir1 端口数)`，即先输出后输入、各自从 0 起。
        绝不能从 Simulink 块的 `Ports` 属性反推——`Ports=[4,6]` 反推会得到方向相反的序列。
        """
        return list(range(len(self.out_ports))) + list(range(len(self.in_ports)))

    def build_userdata(self, override: UserDataFields | None = None) -> str:
        """构造完整 UserData（设计 §4.3 的字段序）。

        格式：`DataVer:2,<aedt绝对路径>,<project>,<design>,<analysis>,<实例名>,<dir0数>,<dir1数>,<dir0名字...>,<dir1名字...>,<索引...>`
        名字段与计数字段同序：先 dir0（输出信号）后 dir1（输入信号）。
        依据：用户手工 Link 后 GUI 写出的真值 `...,6,4,iA,iB,iC,wm,THM,Te,uA,uB,uC,TL,0,1,2,3,4,5,0,1,2,3`——
        计数 6 后紧跟的 6 个名字全是 dir0，计数 4 后紧跟的 4 个名字全是 dir1，计数与名字严格对齐。
        """
        f = override or UserDataFields()
        out_n = f.out_n if f.out_n is not None else len(self.out_ports)
        in_n = f.in_n if f.in_n is not None else len(self.in_ports)
        out_names = f.out_names if f.out_names is not None else [p.name for p in self.out_ports]
        in_names = f.in_names if f.in_names is not None else [p.name for p in self.in_ports]
        idx = f.indices if f.indices is not None else self.indices()
        fields = [
            USERDATA_PREFIX + str(self.aedt_path),
            f.project or self.project,
            f.design or self.design,
            f.analysis or self.analysis,
            f.instance or self.instance,
            str(out_n),
            str(in_n),
            *out_names,
            *in_names,
            *[str(i) for i in idx],
        ]
        return ",".join(fields)


@dataclass
class UserDataFields:
    """UserData 的可覆盖字段；验收「不一致」场景靠它把某个字段人为改错（设计 §6.3 F3 不一致）。

    None = 用 BindingSpec 推出的正确值。
    """

    project: str | None = None
    design: str | None = None
    analysis: str | None = None
    instance: str | None = None
    out_n: int | None = None
    in_n: int | None = None
    in_names: list[str] | None = None
    out_names: list[str] | None = None
    indices: list[int] | None = None


@dataclass
class BindingResult:
    """一个块的实施结果。

    失败时 message 必须是四段式：`阶段 | 对象 | 判据 | 实测值`（设计 §6.1）。
    成功时 message 为空串。
    """

    instance: str = ""
    comp_name: str = ""
    status: str = "pending"  # pending / ok / failed
    stage: str = ""
    message: str = ""
    browse_method: str = ""
    userdata_written: str = ""  # 脚本写回的 UserData（验收读数用）
    userdata_readback: str = ""  # 写回后读回的 UserData
    readback_after_ok: str = ""  # 点 OK 后、写回前的读回（实测末尾索引全 -1，仅留档）
    checks: list[tuple[str, str, str, str]] = field(default_factory=list)
    # checks 每项 = (字段, 期望, 实际, 结论)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def fail(self, stage: str, obj: str, criterion: str, actual: str, browse_method: str | None = None) -> None:
        """按设计 §6.1 的四段式固定格式记失败。"""
        self.status = "failed"
        self.stage = stage
        self.message = f"{stage} | {obj} | {criterion} | {actual}"
        if browse_method is not None:
            self.browse_method = browse_method
