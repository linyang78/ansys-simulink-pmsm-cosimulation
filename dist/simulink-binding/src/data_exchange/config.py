"""配置装载：超时阈值与块路径模板。

对应设计 `docs/design/simulink-binding.md` §2.3（三种异常与超时）、§4.1 第 1 步（块路径）、§4.2（文件对话框）、§5.1（`config/base.yaml`）。
配置只放可调阈值，不放判据——判据写死在代码里，改配置不该改掉验收条件。
"""

from __future__ import annotations

from pathlib import Path

import yaml

# 项目根：src/data_exchange/config.py → 上两级
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "base.yaml"


class ConfigError(Exception):
    """配置文件不可用；消息携带文件路径与原因，由入口脚本映射为退出码 3。"""


class Config:
    """运行期阈值。默认值与设计 §2.3 / §4.2 正文一致，`config/base.yaml` 可覆盖。"""

    __slots__ = (
        "block_path",
        "close_wait_s",
        "dialog_class",
        "dialog_host_exe",
        "dialog_title",
        "engine_ready_s",
        "file_dialog_title",
        "file_dialog_wait_s",
        "poll_interval_s",
        "step_timeout_s",
        "window_wait_s",
    )

    def __init__(
        self,
        window_wait_s: float = 60.0,  # 弹窗未出现超时（设计 §2.3）
        close_wait_s: float = 120.0,  # 点 OK 后等窗口销毁；超时判卡死并杀引擎（设计 §2.3）
        poll_interval_s: float = 0.2,  # 窗口轮询间隔（设计 §2.2：200 ms）
        step_timeout_s: float = 30.0,  # 窗口内单步操作（勾选 / Browse / OK）超时（设计 §2.3）
        file_dialog_wait_s: float = 10.0,  # 点 Browse 后等原生文件对话框（实测 0.2 s 内出现）
        engine_ready_s: float = 300.0,  # MATLAB 引擎启动就绪
        block_path: str = "simulink/User-Defined Functions/S-Function",
        dialog_title: str = "Simplorer Link Assignment Dialog",
        dialog_class: str = "#32770",
        dialog_host_exe: str = "Sim2SimDialog.exe",
        file_dialog_title: str = "打开",
    ) -> None:
        self.window_wait_s = float(window_wait_s)
        self.close_wait_s = float(close_wait_s)
        self.poll_interval_s = float(poll_interval_s)
        self.step_timeout_s = float(step_timeout_s)
        self.file_dialog_wait_s = float(file_dialog_wait_s)
        self.engine_ready_s = float(engine_ready_s)
        self.block_path = str(block_path)
        self.dialog_title = str(dialog_title)
        self.dialog_class = str(dialog_class)
        self.dialog_host_exe = str(dialog_host_exe)
        self.file_dialog_title = str(file_dialog_title)

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"Config(block_path={self.block_path!r}, window_wait_s={self.window_wait_s})"


def load_config(path: str | Path | None = None) -> Config:
    """读 `config/base.yaml`；文件不存在时用设计默认值。

    未知配置项直接报错——拼错的键静默失效，等于改不动阈值还以为改了。
    """
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not cfg_path.is_file():
        return Config()
    try:
        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"配置 | {cfg_path} | 可读且是合法 YAML | {type(exc).__name__}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"配置 | {cfg_path} | 顶层是键值映射 | 读到 {type(raw).__name__}")
    known = set(Config.__slots__)
    unknown = sorted(set(raw) - known)
    if unknown:
        raise ConfigError(f"配置 | {cfg_path} | 只含已知配置项 | 未知项 {unknown}")
    try:
        return Config(**raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"配置 | {cfg_path} | 配置值类型正确 | {exc}") from exc
