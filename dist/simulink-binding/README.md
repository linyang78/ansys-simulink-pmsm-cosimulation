# simulink-binding — Twin Builder ⇄ Simulink 绑定自动化

自包含工具包。给定一个 Twin Builder 工程文件（`.aedt`），为其中每个 `SimulinkData` 元件生成一个独立的
Simulink 模型文件（`.slx`），模型内的 `AnsoftSFunction` 块已完成信号绑定。

**这个包不依赖原项目**，拷走即可用。

## 调用契约

### 命令行

```powershell
python scripts/bind_simulink.py --aedt <path.aedt> --out-dir <dir>
```

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `--aedt` | 是 | — | `.aedt` 绝对或相对路径。**只读**，不修改源文件 |
| `--out-dir` | 否 | `.thincoder/tmp/simulink-binding` | 输出目录，不存在则创建 |
| `--dry-run` | 否 | — | 只解析并打印，不启动 MATLAB、不生成文件 |
| `--config` | 否 | `config/base.yaml` | 配置文件 |
| `--fault-expected-design` | 否 | — | 验收辅助：故意把期望 design 改错，模拟核验失败 |

### 退出码

| 码 | 含义 | agent 应如何处理 |
|---|---|---|
| 0 | 全部块绑定并核验通过 | 成功，读取 `<out-dir>/<design名>.slx` |
| 1 | 部分块失败 | 检查 stdout 的结果表，逐块看 `FAIL` 行 |
| 2 | 解析失败 | `.aedt` 路径错误 / 不可读 / 无 `SimulinkData` 元件。**不要重试**，是输入问题 |
| 3 | 引擎环境失败 | MATLAB 起不来 / 输出目录不可创建。检查环境后**可重试一次** |

### 输出格式

stdout 为人类可读文本（中文）。关键结构：

```
解析结果：N 个 SimulinkData 元件（<aedt路径>）
[1] CompName=<名字>  design=<设计名>  instance=<实例名>  block=<块名>  id=<数字>  analysis=<分析名>
    dir0=<n>(<信号名列表>)  dir1=<m>(<信号名列表>)
    UserData=<完整绑定串>

── 绑定 <CompName>（instance=<实例名> block=<块名> design=<设计名>）
   ok  用时 9.4s
   ...

核验块 Blk=<块名>（CompName=<名字>）：
  | 字段 | 期望 | 实际 | 结论 |
  ...

结果：通过 N / 失败 M（共 K 块）
  OK   <块名> (<CompName>)
  FAIL <块名> (<CompName>)  <四段式错误信息>
输出模型：<输出目录>
```

错误信息为固定四段式：`阶段 | 对象 | 判据 | 实测值`。

### 产物

```
<out-dir>/<design名>.slx
```

- 每个 `SimulinkData` 元件一个文件
- 文件名取 `.aedt` 内的 design 名，**在 `.aedt` 内唯一**
- 同 design 有多个元件时，第二个起追加 `_2`、`_3`
- 已有同名文件时追加序号，**不覆盖**

## 环境要求

| 项 | 要求 | 说明 |
|---|---|---|
| Python | 3.10+ | 用了 `str \| Path` 等新语法 |
| Python 包 | `pyyaml` | 唯一第三方导入依赖 |
| `matlabengine` | 24.2 | 必须与 MATLAB 版本配对 |
| `pywinauto` | 0.6.x | 操作模态对话框 |
| `psutil` | — | 进程树查询 |
| `pywin32` | — | `win32gui` / `win32process` |
| MATLAB | R2024b | 路径见下 |
| Ansys AEDT | 2026 R1 | 提供 `AnsoftSFunction.mexw64` 与 `Sim2SimDialog.exe` |

本机已验证的路径：

```
Python       C:\Env\miniconda3\envs\pmsm\python.exe
MATLAB       E:\Program Files\MATLAB\R2024b
AnsoftSFunction  E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b
```

**换机器时**：改 `config/base.yaml` 无需改动；MATLAB 路径由 `matlabengine` 自行配对；
`AnsoftSFunction` 位置由 MATLAB 的 `path` 决定，需确保该目录在 MATLAB 搜索路径上。

## 运行前提

1. **Twin Builder 引擎需就绪**。两种方式：
   - 提前打开 AEDT 并加载目标 `.aedt`（推荐，快）
   - 让工具触发：对话框会自行拉起 AEDT，但需要等待较长时间
2. **运行期间不要手动操作弹出的对话框**。工具会自动勾选、选文件、选 design、点 OK
3. **同一时刻只跑一个实例**。多个实例会争抢同名窗口

## 调用的典型模式

### Agent 的第一步：dry-run 探路

```python
import subprocess, json, sys

r = subprocess.run(
    [sys.executable, "scripts/bind_simulink.py", "--aedt", aedt, "--dry-run"],
    capture_output=True, text=True, encoding="utf-8",
)
if r.returncode != 0:
    raise RuntimeError(f"解析失败：{r.stdout}{r.stderr}")
# 从 stdout 解析出元件清单，决定是否继续
```

### 正式生成

```python
r = subprocess.run(
    [sys.executable, "scripts/bind_simulink.py",
     "--aedt", aedt, "--out-dir", out_dir],
    capture_output=True, text=True, encoding="utf-8", timeout=1800,
)
# returncode: 0 成功 / 1 部分失败 / 2 解析失败 / 3 环境失败
```

**建议超时**：每个元件约 10–20 秒，`timeout = 块数 × 60 + 300` 秒。

### 以库方式调用（更细粒度）

```python
import sys
sys.path.insert(0, "src")

from data_exchange.aedt_parser import parse_aedt

specs = parse_aedt("path/to/project.aedt")
for s in specs:
    print(s.comp_name, s.design, s.instance, s.block_name)
    print("  dir0:", [p.name for p in s.out_ports])
    print("  dir1:", [p.name for p in s.in_ports])
    print("  indices:", s.indices())
    print("  UserData:", s.build_userdata())
```

`parse_aedt()` 是纯文本解析，**不需要 MATLAB**，可安全用于批量预分析。

## 数据模型

```python
@dataclass(frozen=True)
class Port:
    index: int
    name: str       # 如 "iA" / "uA"
    direction: int  # 1 = 输入到 Twin Builder；0 = 输出到 Simulink

@dataclass(frozen=True)
class BindingSpec:
    aedt_path: Path
    project: str
    design: str
    analysis: str
    comp_name: str      # 如 "SimulinkData10"
    instance: str       # 如 "MDL1"（.aedt 内原文，可能重复）
    vector_size: int
    ports: list[Port]

    # 派生
    block_name: str          # Simulink 块名，去重后（MDL1 / MDL1_2）
    out_ports: list[Port]    # direction == 0
    in_ports: list[Port]     # direction == 1
    def indices(self) -> list[int]:
        return list(range(len(self.out_ports))) + list(range(len(self.in_ports)))
    def build_userdata(self) -> str: ...
```

**注意 `instance` 与 `block_name` 的区别**：
- `instance` 是 `.aedt` 里的原文，Twin Builder 用它找元件，**必须保持原样**
- `block_name` 是 Simulink 模型内的块名，同模型内不能重名，故去重

## 已知限制

1. **一次只处理一个 `.aedt`**。多工程请循环调用
2. **不改已有 `.slx`**，只新建空白模型
3. **不连信号线**，只放块并完成绑定
4. **不修改 `.aedt`**，纯只读
5. **同一 Simulink 模型内放多个块的问题未解决**，故采用「一元件一模型」
6. **仅 Windows**。依赖 `pywin32` 与 `pywinauto` 的 Win32 后端

## 自检

```powershell
# 语法与风格
python -m ruff check src/ scripts/ tests/

# 单测（11 个，纯解析，不需要 MATLAB）
python -m pytest tests/ -q
```

## 目录结构

```
simulink-binding/
├── README.md                      本文件
├── docs/
│   └── USERDATA-FORMAT.md         UserData 字段格式说明
├── src/
│   ├── data_exchange/
│   │   ├── models.py              数据类
│   │   ├── aedt_parser.py         .aedt 解析（纯文本，无需 MATLAB）
│   │   └── config.py              配置读取
│   └── simulink_controller/
│       ├── dialog.py              窗口线程（pywinauto）
│       ├── binder.py              MATLAB 引擎管理 + 握手
│       └── verifier.py            核验与比对表
├── scripts/
│   └── bind_simulink.py           命令行入口
├── tests/
│   └── test_aedt_parser.py        解析器单测
└── config/
    └── base.yaml                  超时阈值与控件标识
```
