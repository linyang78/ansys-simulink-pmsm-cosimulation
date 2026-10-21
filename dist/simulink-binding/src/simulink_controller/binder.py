"""MATLAB 引擎线程与握手：建块、触发弹窗、读回、写回 UserData、保存。

对应设计 `docs/design/simulink-binding.md` §2.2（三个执行体与同步）、§2.3（三种异常）、
§4.1（单块动作序列的引擎侧）、§4.4（块间状态污染）、§4.5（每块完成即保存）。

两条决定架构的实测事实：
1. `set_param(blk,'FunctionName','AnsoftSFunction')` 同步阻塞并弹出模态对话框，关窗前不返回——
   它必须以 `background=True` 提交，由窗口线程接手，主线程只轮询「窗口是否消失」；
2. 点 OK 之后读回的 `UserData` 末尾索引全为 `-1`（映射并未建立），
   故第 12 步由脚本按设计 §4.3 的规则构造完整串并 `set_param(blk,'UserData',构造串)` 写回。
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from data_exchange.models import (
    STAGE_ADD_BLOCK,
    STAGE_CLOSE,
    STAGE_SAVE,
    STAGE_TRIGGER,
    STAGE_WRITE,
    BindingResult,
)
from simulink_controller.dialog import MatlabEngineView, WindowWorker, dialog_still_open

if TYPE_CHECKING:  # 仅类型引用，运行期不依赖
    from data_exchange.config import Config
    from data_exchange.models import BindingSpec

S_FUNCTION_NAME = "AnsoftSFunction"
ENGINE_QUIT_TIMEOUT_S = 15.0


class EngineError(Exception):
    """引擎/环境失败（对应退出码 3，设计 §6.2）。消息本身按四段式组织。"""


class MatlabHost:
    """持有一个 MATLAB 引擎；卡死时整引擎重建（设计 §2.3、§4.4 ③）。"""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.eng: Any = None
        self.pid: int | None = None
        self.restarts = 0

    # ---- 生命周期 -------------------------------------------------------
    def start(self) -> None:
        """启动引擎并等它就绪；记录本次拉起的引擎 PID（窗口判据③用）。"""
        try:
            import matlab.engine
        except ImportError as exc:
            raise EngineError(f"引擎 | Python 环境 | 可 import matlab.engine | {exc}") from exc
        try:
            import psutil
        except ImportError as exc:
            raise EngineError(f"引擎 | Python 环境 | 可 import psutil | {exc}") from exc

        before = self._matlab_pids()
        try:
            future = matlab.engine.start_matlab(background=True)
        except Exception as exc:
            raise EngineError(f"引擎 | MATLAB R2024b | 引擎可启动 | {type(exc).__name__}: {exc}") from exc

        ready = threading.Event()
        box: dict[str, Any] = {}

        def _wait() -> None:
            try:
                box["eng"] = future.result()
            except Exception as exc:  # noqa: BLE001
                box["err"] = exc
            finally:
                ready.set()

        threading.Thread(target=_wait, daemon=True, name="eng-start").start()
        if not ready.wait(timeout=self.cfg.engine_ready_s):
            raise EngineError(f"引擎 | MATLAB R2024b | {self.cfg.engine_ready_s:g}s 内就绪 | 超时未返回")
        if "err" in box:
            raise EngineError(
                f"引擎 | MATLAB R2024b | 引擎可启动 | {type(box['err']).__name__}: {box['err']}"
            )
        self.eng = box["eng"]

        new_pids = self._matlab_pids() - before
        if not new_pids:
            raise EngineError("引擎 | MATLAB.exe | 能识别本次拉起的引擎进程 | 启动前后 MATLAB 进程集合无新增")
        # 取最深的一个：启动外壳与真正的引擎宿主都在新增集合里
        self.pid = max(new_pids, key=lambda p: len(psutil.Process(p).parents()))

    @staticmethod
    def _matlab_pids() -> set[int]:
        """本进程全部后代里可执行名为 `MATLAB.exe` 的 PID。"""
        import psutil

        found: set[int] = set()
        for child in psutil.Process().children(recursive=True):
            try:
                if child.name().lower() == "matlab.exe":
                    found.add(child.pid)
            except psutil.Error:
                continue
        return found

    def stop(self) -> None:
        """优雅退出；`eng.quit()` 实测会卡，故限时后强制 kill。"""
        if self.eng is None and self.pid is None:
            return
        done = threading.Event()

        def _quit() -> None:
            try:
                if self.eng is not None:
                    self.eng.quit()
            except Exception:  # noqa: BLE001, S110 —— quit 失败时下面会强制 kill，无需日志
                pass
            finally:
                done.set()

        threading.Thread(target=_quit, daemon=True, name="eng-quit").start()
        done.wait(timeout=ENGINE_QUIT_TIMEOUT_S)
        self.kill()

    def kill(self) -> None:
        """强制杀引擎进程树（设计 §2.3「弹窗卡死」）。"""
        if self.pid is not None:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(self.pid)],
                capture_output=True,
                check=False,
            )
        self.eng = None
        self.pid = None

    def restart(self) -> None:
        self.restarts += 1
        self.kill()
        self.start()

    @property
    def view(self) -> MatlabEngineView:
        return MatlabEngineView(self.pid)

    # ---- 引擎侧动作 -----------------------------------------------------
    def eval(self, expr: str, obj: str, criterion: str) -> Any:
        """同步求值；引擎异常转成 `EngineError`（四段式）。"""
        if self.eng is None:
            raise EngineError(f"引擎 | {obj} | 引擎在线 | 引擎已退出")
        try:
            return self.eng.eval(expr, nargout=0)
        except Exception as exc:
            raise EngineError(f"引擎 | {obj} | {criterion} | {_format_engine_error(exc)}") from exc

    def eval_background(self, expr: str, obj: str, criterion: str) -> None:
        """异步提交（`background=True`）——阻塞调用（`set_param` 改 FunctionName）走这条。"""
        if self.eng is None:
            raise EngineError(f"引擎 | {obj} | 引擎在线 | 引擎已退出")
        try:
            self.eng.eval(expr, nargout=0, background=True)
        except Exception as exc:
            raise EngineError(f"引擎 | {obj} | {criterion} | {_format_engine_error(exc)}") from exc


def _format_engine_error(exc: Exception) -> str:
    """把 matlab.engine 的异常压成一行（`MatlabExecutionError` 的文本带长栈）。"""
    return f"{type(exc).__name__}: {str(exc).replace(chr(10), ' ')[:600]}"


def _split_engine_error(exc: EngineError) -> tuple[str, str]:
    """`引擎 | 对象 | 判据 | 实测值` → (判据, 实测值)；拆不出就整体当实测值。"""
    parts = str(exc).split(" | ")
    if len(parts) >= 4:
        return parts[2], " | ".join(parts[3:])
    return "步骤成功", str(exc)


def model_name(out_slx: Path) -> str:
    """由 `.slx` 路径推出 MATLAB 模型名：非标识符字符换成 `_`，首字符不是字母时加前缀 `m_`。

    文件名不变，只影响 MATLAB 内的模型名——`new_system('_gen')` 会被 MATLAB 拒绝（模型名须是合法函数名）。
    """
    name = re.sub(r"[^0-9A-Za-z_]", "_", out_slx.stem)
    if not re.match(r"[A-Za-z]", name):
        name = "m_" + name
    return name


def _mat_str(value: str) -> str:
    """MATLAB 字符向量字面量：单引号内部的单引号双写。"""
    return "'" + value.replace("'", "''") + "'"


# ---- 单块引擎侧动作（设计 §4.1 步 1 / 2 / 11 / 12 / 14） -------------------


def add_block(host: MatlabHost, blk_path: str, cfg: Config) -> None:
    """步 1：把 S-Function 块加到新建的空白模型里。"""
    expr = f"add_block({_mat_str(cfg.block_path)}, {_mat_str(blk_path)});"
    host.eval(expr, f"Blk={blk_path}", "块可加到空白模型")


def trigger_dialog(host: MatlabHost, blk_path: str) -> None:
    """步 2：改 `FunctionName` 触发模态对话框（阻塞调用，异步提交）。"""
    expr = f"set_param({_mat_str(blk_path)},'FunctionName',{_mat_str(S_FUNCTION_NAME)});"
    host.eval_background(expr, f"Blk={blk_path}", "可异步提交 set_param FunctionName")


def read_userdata(host: MatlabHost, blk_path: str) -> str:
    """步 11 / 13：读回 `UserData`（`Parameters` 不读——实测不作判据，设计 §4.3）。"""
    expr = f"get_param({_mat_str(blk_path)},'UserData')"
    try:
        raw = host.eng.eval(expr, nargout=1) if host.eng is not None else None
    except Exception as exc:
        raise EngineError(
            f"引擎 | Blk={blk_path} | 能读回 UserData | {_format_engine_error(exc)}"
        ) from exc
    return "" if raw is None else str(raw)


def write_userdata(host: MatlabHost, blk_path: str, userdata: str) -> None:
    """步 12：把构造好的 UserData 写回块（直接 `set_param`，不经 `eval` 字符串）。"""
    expr = f"set_param({_mat_str(blk_path)},'UserData',{_mat_str(userdata)});"
    host.eval(expr, f"Blk={blk_path}", "UserData 可写回")


def save_model(host: MatlabHost, model: str, out_slx: Path) -> None:
    """步 14：保存模型到指定路径（设计 §4.5 每块完成即保存）。

    ``save_system(name)`` 只按模型名存到默认位置，不会写到指定文件（实测 2026-10-20：
    报成功但目标目录里没有 .slx）。必须用 ``save_system(name, path)``。
    """
    host.eval(
        f"save_system({_mat_str(model)}, {_mat_str(str(out_slx))})",
        f"{out_slx}",
        "模型可保存到指定路径",
    )


# ---- 单块全流程 -----------------------------------------------------------


def bind_block(
    host: MatlabHost,
    spec: BindingSpec,
    blk_path: str,
    out_slx: Path,
    cfg: Config,
) -> tuple[BindingResult, bool]:
    """跑完一个块的「建块 → 触发 → 窗口操作 → 关窗」（设计 §4.1 步 1–10）。

    返回 (result, engine_dead)：engine_dead=True 表示本块让引擎进入不可信状态，
    调用方须按设计 §2.3 杀掉引擎并重建。
    读回 / 写回 / 核验 / 保存由调用方接在返回之后（它们需要 verifier）。
    """
    result = BindingResult(instance=spec.block_name, comp_name=spec.comp_name)

    # 步 1：建块
    try:
        add_block(host, blk_path, cfg)
    except EngineError as exc:
        criterion, actual = _split_engine_error(exc)
        result.fail(STAGE_ADD_BLOCK, f"Blk={blk_path}", criterion, actual)
        return result, False

    # 步 2：触发（异步提交，立即返回；引擎侧阻塞到对话框关闭）
    try:
        trigger_dialog(host, blk_path)
    except EngineError as exc:
        criterion, actual = _split_engine_error(exc)
        result.fail(STAGE_TRIGGER, f"Blk={blk_path}", criterion, actual)
        return result, False

    # 步 3–9：窗口线程按 §2.2 判据接手
    worker = WindowWorker(spec, result, cfg, host.view)
    worker.start()

    # 步 10：等窗口线程收尾（上限 = 窗口等待 + 关窗等待 + 单步余量）
    budget = cfg.window_wait_s + cfg.close_wait_s + cfg.step_timeout_s
    if not worker.done.wait(timeout=budget):
        result.fail(
            STAGE_CLOSE,
            f"Blk={blk_path}",
            f"窗口线程在 {budget:g}s 内结束",
            f"done 未置位；ok_clicked={worker.ok_clicked}",
        )
        return result, True

    if result.status == "failed":
        # 窗口动作失败：引擎可能仍阻塞在 set_param 上——杀掉重建，绝不复用
        return result, True
    if not worker.ok_clicked:
        result.fail(STAGE_CLOSE, f"Blk={blk_path}", "点了 OK 才进入读回", "窗口线程未执行 OK 点击")
        return result, True

    # 点 OK 后等窗口销毁 → set_param 解阻（设计 §2.2 步 4、§2.3「弹窗卡死」）
    hwnd = worker.hwnd
    deadline = time.monotonic() + cfg.close_wait_s
    while hwnd is not None and dialog_still_open(hwnd, cfg.dialog_class, cfg.dialog_title):
        if time.monotonic() >= deadline:
            result.fail(
                STAGE_CLOSE,
                f"Blk={blk_path}",
                f"点 OK 后 {cfg.close_wait_s:g}s 内窗口销毁",
                f"hwnd={hwnd} 仍在（判「弹窗卡死」，杀引擎重建）",
            )
            return result, True
        time.sleep(cfg.poll_interval_s)

    return result, False


__all__ = [
    "STAGE_SAVE",
    "STAGE_WRITE",
    "S_FUNCTION_NAME",
    "EngineError",
    "MatlabHost",
    "add_block",
    "bind_block",
    "model_name",
    "read_userdata",
    "save_model",
    "trigger_dialog",
    "write_userdata",
]
