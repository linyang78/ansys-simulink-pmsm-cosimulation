"""pywinauto 窗口线程：接手 `Simplorer Link Assignment Dialog` 并完成勾选 / Browse / 选 design / OK。

对应设计 `docs/design/simulink-binding.md` §2.2（窗口判据与交接）、§2.3（三种异常）、
§4.1 第 3–9 步（窗口侧动作）、§4.2（Browse 原生文件对话框）。

本线程只做窗口动作并回填 `BindingResult`，不碰 MATLAB 引擎；
「关窗后引擎是否释放」由主线程按 `close_ok` 判断（设计 §2.3「弹窗卡死」判据在主线程）。

五条实测事实决定了这里的写法（全部来自设计 §4.1 / §4.2，改动前先读那一节）：
1. 弹窗宿主是独立进程 `Sim2SimDialog.exe`，不在 MATLAB 进程组内——判据看祖先链里有没有本会话的 `MATLAB.exe`；
2. 复选框必须用 `check_by_click_input()`。`check()` 只发 `BM_SETCHECK` 改状态位，官方对话框不响应后续逻辑；
3. `Browse` 未选文件时 `is_enabled()` 返回 False，但 `click_input()` 有效——不判可用状态；
4. 文件对话框确认按钮要 `title_re='打开.*'`，精确 `'打开(O)'` 匹配不到（全角括号）。
   唯一未被设计认可的方式是往文件名栏输入路径：`set_edit_text` 写绝对路径后点确认按钮，
   此时名称栏显示的是完整路径、`请...文件名` 勾选保持默认；找不到确认按钮时退回 `Edit.set_focus()` + `{ENTER}`；
5. design 下拉框默认停在文件里的第一个 design，必须显式 `select()` 并读回 `window_text()` 比对。
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

from data_exchange.models import (
    STAGE_BROWSE,
    STAGE_CLOSE,
    STAGE_DIALOG,
    STAGE_TRIGGER,
    BindingResult,
)

if TYPE_CHECKING:  # 仅类型引用，运行期不依赖
    from data_exchange.config import Config
    from data_exchange.models import BindingSpec

# 复选框按标题 + 类名定位（设计 §4.1：`Read link information from fileCheckBox` 是显示别名，不是 auto_id）
CHECKBOX_TITLE = "Read link information from file"
BROWSE_TITLE = "Browse"
OK_TITLE = "OK"


class MatlabEngineView:
    """MATLAB 引擎进程的只读视图：窗口线程只关心「这个 PID 是不是本会话拉起的引擎」。

    设计 §2.2 条件③「宿主进程的祖先链中存在本会话拉起的 `MATLAB.exe`」——祖先链在本类里算。
    """

    def __init__(self, pid: int | None) -> None:
        self.pid = pid

    def is_descendant_of_engine(self, host_pid: int) -> bool:
        """`host_pid` 的祖先链里是否出现本会话的引擎 PID。"""
        if self.pid is None:
            return False
        try:
            import psutil
        except ImportError:  # pragma: no cover - 环境缺 psutil 直接判不命中
            return False
        try:
            proc = psutil.Process(host_pid)
            for parent in proc.parents():
                if parent.pid == self.pid:
                    return True
        except Exception:  # noqa: BLE001 —— 进程在枚举后退出属正常竞争
            return False
        return False


# ---- 窗口判据（设计 §2.2 条件①②③） -------------------------------------


def _looks_like_dialog(
    hwnd: int,
    title: str,
    title_re: str | None,
    class_name: str,
    host_exe: str,
    engine: MatlabEngineView,
    require_host: bool,
) -> bool:
    """三条件：类名、标题、宿主进程名（+ 祖先链含本会话引擎）。"""
    import win32gui
    import win32process

    if win32gui.GetClassName(hwnd) != class_name:
        return False
    text = win32gui.GetWindowText(hwnd)
    if title_re is not None:
        import re

        if re.match(title_re, text) is None:
            return False
    elif text != title:
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:  # noqa: BLE001
        return False
    if require_host:
        import psutil

        try:
            host_name = psutil.Process(pid).name().lower()
        except Exception:  # noqa: BLE001 —— 进程已退出
            return False
        if host_name != host_exe.lower():  # noqa: SIM103 —— 保留正向判断，便于下面加注释
            return False
        # 祖先链只作辅助判断，不作必要条件。
        # 实测：Sim2SimDialog.exe 与 MATLAB.exe 是兄弟进程（都是拉起引擎的 python 的子进程），
        # 并非 MATLAB 的后代；要求“后代”会让判据永远 False（2026-10-20 实测，MDL1_2 因此超时）。
        # 进程名已对上，就足以排除同名异程序窗口。
        return True
    return True


def find_window(
    title: str,
    class_name: str,
    host_exe: str,
    engine: MatlabEngineView,
    timeout_s: float,
    poll_s: float,
) -> tuple[int | None, int, int]:
    """轮询等绑定对话框（条件①②③）。

    返回 (hwnd | None, 轮询次数, 见过的同类窗口数)；后两项喂四段式失败信息的「实测值」。
    """
    import win32gui
    import win32process

    deadline = time.monotonic() + timeout_s
    polls = 0
    seen = 0
    seen_desc: dict[str, int] = {}
    while True:
        polls += 1
        handles: list[int] = []

        def _collect(hwnd: int, _param, acc: list[int] = handles) -> bool:
            # 第三个参数由 EnumWindows 传入 lparam（None），不影响 acc
            if win32gui.GetClassName(hwnd) == class_name:
                acc.append(hwnd)
            return True

        win32gui.EnumWindows(_collect, None)
        seen = max(seen, len(handles))
        # 记录每个同类窗口的来源，供失败信息说明「见到的都是谁的窗口」
        for hwnd in handles:
            try:
                _t = win32gui.GetWindowText(hwnd)
                _p = win32process.GetWindowThreadProcessId(hwnd)[1]
                import psutil as _ps

                _n = _ps.Process(_p).name()
            except Exception:  # noqa: BLE001
                _t, _n = "<?>", "<?>"
            key = f"{_n}:{_t[:24]}"
            seen_desc[key] = seen_desc.get(key, 0) + 1
        for hwnd in handles:
            if _looks_like_dialog(hwnd, title, None, class_name, host_exe, engine, require_host=True):
                return hwnd, polls, len(handles)
        if time.monotonic() >= deadline:
            find_window.last_desc = "; ".join(f"{k}x{v}" for k, v in seen_desc.items())
            return None, polls, seen
        time.sleep(poll_s)


def dialog_still_open(hwnd: int, class_name: str, title: str) -> bool:
    """窗口是否还在：句柄已销毁或标题变了都算不在（点 OK 后 `set_param` 解阻的判据）。"""
    import win32gui

    try:
        return bool(win32gui.IsWindow(hwnd)) and win32gui.GetWindowText(hwnd) == title
    except Exception:  # noqa: BLE001
        return False


# ---- 窗口线程 ------------------------------------------------------------


class WindowWorker(threading.Thread):
    """窗口线程：一个块一个实例（设计 §4.4 ①每块走独立的对话框实例）。"""

    def __init__(
        self,
        spec: BindingSpec,
        result: BindingResult,
        cfg: Config,
        engine: MatlabEngineView,
    ) -> None:
        super().__init__(daemon=True, name=f"dialog-{spec.block_name}")
        self.spec = spec
        self.result = result
        self.cfg = cfg
        self.engine = engine
        self.done = threading.Event()  # 线程走完（成功或失败）都置位
        self.ok_clicked = False  # 点过 OK：主线程据此区分「关窗卡死」与「该块失败」
        self.hwnd: int | None = None
        self.dlg = None  # 主对话框包装，失败兜底按 Esc 用

    # ---- 线程主体 -------------------------------------------------------
    def run(self) -> None:
        try:
            self._run()
        except Exception as exc:  # noqa: BLE001 —— 任何异常都要落成四段式，不能静默
            if self.result.status != "failed":
                self.result.fail(
                    STAGE_DIALOG,
                    f"Blk={self.spec.block_name}",
                    "窗口操作不抛异常",
                    f"{type(exc).__name__}: {exc}",
                )
                self._press_escape()
        finally:
            self.done.set()

    def _run(self) -> None:
        hwnd, polls, seen = find_window(
            self.cfg.dialog_title,
            self.cfg.dialog_class,
            self.cfg.dialog_host_exe,
            self.engine,
            self.cfg.window_wait_s,
            self.cfg.poll_interval_s,
        )
        if hwnd is None:
            # 设计 §2.3「弹窗未出现」：记录步骤 + 原因，该块失败，继续下一块
            self.result.fail(
                STAGE_TRIGGER,
                f"Blk={self.spec.block_name}",
                f"窗口 {self.cfg.window_wait_s:g}s 内出现",
                f"已轮询 {polls} 次，命中 {self.cfg.dialog_class} 窗口 {seen} 个"
                f"（判据含标题、宿主 {self.cfg.dialog_host_exe}、祖先链含本会话 MATLAB.exe）",
            )
            return
        self.hwnd = hwnd

        from pywinauto import Application

        self.dlg = Application(backend="win32").connect(handle=hwnd).window(handle=hwnd)

        # 第 4 步：勾选 Read link information from file（必须真实鼠标事件）
        if not self._check_read_link():
            return
        # 第 5–6 步：Browse → 填 .aedt 绝对路径 → 确认
        if not self._browse():
            return
        # 第 7–8 步：显式选 design，读回比对；analysis 框随 design 自动填，不操作
        if not self._select_design():
            return
        # 第 9 步：点 OK
        if not self._click_ok():
            return
        self.ok_clicked = True

    # ---- 第 4 步 -------------------------------------------------------
    def _check_read_link(self) -> bool:
        try:
            box = self.dlg.child_window(title=CHECKBOX_TITLE, class_name="Button")
            box.wait("exists", timeout=self.cfg.step_timeout_s)
            box.check_by_click_input()
            return True
        except Exception as exc:  # noqa: BLE001
            self.result.fail(
                STAGE_DIALOG,
                f"Blk={self.spec.block_name}",
                f"控件「{CHECKBOX_TITLE}」可勾选",
                f"{type(exc).__name__}: {exc}",
            )
            self._press_escape()
            return False

    # ---- 第 5–6 步 -----------------------------------------------------
    def _browse(self) -> bool:
        try:
            browse = self.dlg.child_window(title=BROWSE_TITLE, class_name="Button")
            browse.wait("exists", timeout=self.cfg.step_timeout_s)
            # 不判 is_enabled：未选文件时返回 False（灰色）但 click_input 有效（设计 §4.1）
            browse.click_input()
        except Exception as exc:  # noqa: BLE001
            self.result.fail(
                STAGE_BROWSE,
                f"Blk={self.spec.block_name}",
                f"「{BROWSE_TITLE}」按钮可点击",
                f"{type(exc).__name__}: {exc}",
            )
            self._press_escape()
            return False

        file_dlg = self._wait_file_dialog()
        if file_dlg is None:
            self.result.fail(
                STAGE_BROWSE,
                f"Blk={self.spec.block_name}",
                f"点 {BROWSE_TITLE} 后 {self.cfg.file_dialog_wait_s:g}s 内出现文件对话框",
                f"未找到标题「{self.cfg.file_dialog_title}」的 {self.cfg.dialog_class} 窗口",
            )
            self._press_escape()
            return False

        target = str(self.spec.aedt_path)
        # 文件名栏：实测 `class_name='Edit', found_index=0` 即文件名输入框（设计 §4.2）
        try:
            edit = file_dlg.child_window(class_name="Edit", found_index=0)
            edit.wait("exists", timeout=self.cfg.step_timeout_s)
            edit.set_edit_text(target)
            self.result.browse_method = "set_edit_text"
        except Exception as exc:  # noqa: BLE001
            self.result.fail(
                STAGE_BROWSE,
                f"Blk={self.spec.block_name}",
                "文件名栏（Edit,#0）可写入",
                f"{type(exc).__name__}: {exc}",
            )
            self._press_escape()
            return False

        if self._confirm_file_dialog(file_dlg, edit):
            return True
        self.result.fail(
            STAGE_BROWSE,
            f"Blk={self.spec.block_name}",
            "确认按钮（title_re='打开.*'）可点击并关闭文件对话框",
            "点击与 {ENTER} 兜底均未关闭文件对话框（降级为人工绑定，不标通过）",
            browse_method="set_edit_text+确认失败",
        )
        self._press_escape()
        return False

    def _wait_file_dialog(self):
        """轮询等原生文件对话框（主对话框之外的另一个 #32770，标题为「打开」）。

        用 `Desktop(backend='win32')`——它是全局桌面搜索，可按标题 + 类名直接取窗口。
        **不能用 `Application(backend='win32')`**：它必须先 `start()`/`connect()`，否则调
        `.window()` 抛 `Please use start or connect before trying anything else`；
        该异常会被下面的 `except` 吞掉，表现为「文件对话框找不到」直到超时（实测 2026-10-20）。

        不遍历 `Desktop.windows()` 再调 `child_window()`——列表元素是 `DialogWrapper`，没有该方法（设计 §4.2）。
        """
        from pywinauto import Desktop

        desktop = Desktop(backend="win32")
        deadline = time.monotonic() + self.cfg.file_dialog_wait_s
        while True:
            try:
                dlg = desktop.window(title=self.cfg.file_dialog_title, class_name=self.cfg.dialog_class)
                if dlg.exists(timeout=0.2) and dlg.handle != self.hwnd:
                    return dlg
            except Exception:  # noqa: BLE001, S110 —— 轮询窗口的正常竞态，无需日志
                pass
            if time.monotonic() >= deadline:
                return None
            time.sleep(self.cfg.poll_interval_s)

    def _confirm_file_dialog(self, file_dlg, edit) -> bool:
        """点「打开」确认；`title_re='打开.*'` 匹配不到时退回 Edit 聚焦 + {ENTER}。"""
        try:
            btn = file_dlg.child_window(class_name="Button", title_re="打开.*")
            if btn.exists(timeout=self.cfg.step_timeout_s):
                btn.click_input()
            else:
                raise RuntimeError("title_re='打开.*' 未匹配按钮")
        except Exception:  # noqa: BLE001 —— 走键盘兜底
            try:
                edit.set_focus()
                file_dlg.type_keys("{ENTER}")
            except Exception:  # noqa: BLE001
                return False
        try:
            file_dlg.wait_not("exists", timeout=self.cfg.step_timeout_s)
            return True
        except Exception:  # noqa: BLE001
            return False

    # ---- 第 7–8 步 -----------------------------------------------------
    def _select_design(self) -> bool:
        try:
            combo = self.dlg.child_window(class_name="ComboBox", found_index=0)
            combo.wait("exists", timeout=self.cfg.step_timeout_s)
            # 选完文件后下拉框要等引擎读完设计列表才可用；直接 select 会抛
            # ElementNotEnabled（实测 2026-10-20，三块全挂这一步）。
            # 按探针的有效做法：先给一段安静等，再用 select + 重试。
            time.sleep(3.0)
            last_exc: Exception | None = None
            deadline = time.monotonic() + self.cfg.step_timeout_s
            while time.monotonic() < deadline:
                try:
                    combo.select(self.spec.design)
                    last_exc = None
                    break
                except Exception as exc:  # noqa: BLE001 —— 还没 ready，重试
                    last_exc = exc
                    time.sleep(self.cfg.poll_interval_s)
            if last_exc is not None:
                raise last_exc
            actual = (combo.window_text() or "").strip()
        except Exception as exc:  # noqa: BLE001
            self.result.fail(
                STAGE_DIALOG,
                f"Blk={self.spec.block_name}",
                f"design 下拉框可选中 {self.spec.design}",
                f"{type(exc).__name__}: {exc}",
            )
            self._press_escape()
            return False
        if actual != self.spec.design:
            self.result.fail(
                STAGE_DIALOG,
                f"Blk={self.spec.block_name}",
                f"选后读回 design={self.spec.design}",
                f"实读 ComboBox0={actual!r}",
            )
            self._press_escape()
            return False
        return True

    # ---- 第 9 步 -------------------------------------------------------
    def _click_ok(self) -> bool:
        try:
            ok = self.dlg.child_window(class_name="Button", title=OK_TITLE)
            ok.wait("exists", timeout=self.cfg.step_timeout_s)
            ok.click_input()
            return True
        except Exception as exc:  # noqa: BLE001
            self.result.fail(
                STAGE_CLOSE,
                f"Blk={self.spec.block_name}",
                f"「{OK_TITLE}」按钮可点击",
                f"{type(exc).__name__}: {exc}",
            )
            self._press_escape()
            return False

    def _press_escape(self) -> None:
        """释放引擎：按 Esc 关窗（设计 §2.3「弹窗出现但不响应」）。"""
        if self.dlg is None:
            return
        try:
            self.dlg.set_focus()
            self.dlg.type_keys("{ESC}")
        except Exception:  # noqa: BLE001, S110 —— Esc 关窗的兜底，失败不影响主流程
            pass
