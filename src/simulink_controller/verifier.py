"""绑定结果核验：读回 UserData，与解析出的期望值逐字段比对，输出比对表。

对应设计 `docs/design/simulink-binding.md` §4.3（绑定成功判据）、§6.1（错误信息四段式）、§6.3（F3 比对表）。

三条判据（全部满足才算成功）：
1. `UserData` 以 `DataVer:2,` 开头；
2. `UserData` 含 `.aedt` 绝对路径、design 名、实例名三个子串；
3. `UserData` 末尾索引序列不是全 `-1`，且等于 `range(dir0 端口数) + range(dir1 端口数)`。

**`Parameters` 不作判据**（实测点 OK 后读回空串、旧模型里是 `-1`，取值不稳定）。
索引序列不按字符串位置反推（那是单样本反推的语义），只按「构造串 == 读回串」逐字节比对——
构造串由 `BindingSpec.build_userdata()` 生成，比对是字符串相等，不解析任何字段位置。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from data_exchange.models import STAGE_VERIFY, USERDATA_PREFIX, BindingResult

if TYPE_CHECKING:  # 仅类型引用，运行期不依赖
    from data_exchange.models import BindingSpec

F_PREFIX = "UserData 前缀"
F_PATH = "UserData 含 .aedt 路径"
F_DESIGN = "UserData 含 design"
F_INSTANCE = "UserData 含 instance"
F_INDICES = "UserData 末尾索引"
F_EXACT = "UserData 全文"

_SHOW = 40


def _short(value: str | None, limit: int = _SHOW) -> str:
    if value is None:
        return "<None>"
    text = value.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _tail(userdata: str, count: int) -> list[str]:
    """UserData 末尾 `count` 个字段（索引段长度 = 两向端口数之和）。"""
    parts = userdata.split(",")
    return parts[-count:] if count > 0 else []


@dataclass(frozen=True)
class Expected:
    """核验的期望值。单独抽出来是为了「不一致」场景能人为改错一处，不动解析结果（设计 §6.3 F3 不一致）。"""

    userdata: str
    aedt_path: str
    design: str
    instance: str

    @classmethod
    def from_spec(cls, spec: BindingSpec) -> Expected:
        return cls(
            userdata=spec.build_userdata(),
            aedt_path=str(Path(spec.aedt_path)),
            design=spec.design,
            instance=spec.instance,
        )

    def with_design(self, design: str) -> Expected:
        """验收辅助：把期望 design 换成另一个值（等长替换，全文比对仍能反映差异）。"""
        return replace(self, design=design)


def build_checks(exp: Expected, userdata: str | None, n_ports: int) -> list[tuple[str, str, str, str]]:
    """字段比对表：(字段, 期望, 实际, 结论)。顺序固定，每行判据独立，四列齐全。"""
    ud = userdata or ""
    expect_idx = ",".join(exp.userdata.split(",")[-(n_ports):] if n_ports else [])
    actual_idx = ",".join(_tail(ud, n_ports))
    rows: list[tuple[str, str, str, bool]] = [
        (F_PREFIX, USERDATA_PREFIX, _short(ud), ud.startswith(USERDATA_PREFIX)),
        (F_PATH, exp.aedt_path, ud if exp.aedt_path in ud else _short(ud), exp.aedt_path in ud),
        (F_DESIGN, exp.design, ud if exp.design in ud else _short(ud), exp.design in ud),
        (F_INSTANCE, exp.instance, ud if exp.instance in ud else _short(ud), exp.instance in ud),
        (F_INDICES, expect_idx, actual_idx, actual_idx == expect_idx and "-1" not in actual_idx.split(",")),
        (F_EXACT, _short(exp.userdata, 120), _short(ud, 120), ud == exp.userdata),
    ]
    return [(name, e, a, "一致" if ok else "不符") for name, e, a, ok in rows]


def verify_block(
    spec: BindingSpec,
    userdata: str | None,
    expected: Expected | None = None,
) -> BindingResult:
    """核验一个块；返回填好 `checks` 的 BindingResult（status = ok / failed）。

    判据一至三（前缀 / 三个子串 / 索引）任一不符即判失败；`UserData 全文` 行只作读数呈现
    （端口名与字段序来自实测，不单独作为通过条件，避免把单样本语义写成判据）。
    """
    exp = expected or Expected.from_spec(spec)
    result = BindingResult(instance=spec.block_name, comp_name=spec.comp_name)
    ud = userdata or ""
    result.checks = build_checks(exp, userdata, len(spec.ports))

    failed = [
        name
        for name, _e, _a, verdict in result.checks
        if verdict != "一致" and name != F_EXACT
    ]
    if not failed:
        result.status = "ok"
        return result

    result.fail(
        STAGE_VERIFY,
        f"Blk={spec.block_name} instance={spec.instance}",
        "；".join(failed) + " 全部一致",
        f"UserData={_short(ud, 160)}",
    )
    return result
