# Twin Builder ⇄ Simulink 绑定自动化 — 使用说明

给定一个 Twin Builder 工程文件（`.aedt`），自动为其中每个 `SimulinkData` 元件生成一个独立的 Simulink 模型，
模型里的 `AnsoftSFunction` 块已完成信号绑定，可直接用于联合仿真。

替代的手工流程是：新建 `.slx` → 加 S-Function → 改名 `AnsoftSFunction` → 弹窗里勾选 `Read link information from file`
→ Browse 选 `.aedt` → 选 design → 逐个点 Link → 点 OK。一个元件一次，重复且易错。

## 快速开始

```powershell
# 1) 先看会解析出什么（不启动 MATLAB，秒级返回）
& 'C:\Env\miniconda3\envs\pmsm\python.exe' scripts\bind_simulink.py `
    --aedt models\manual\RotorySimulink_thincoder.aedt --dry-run

# 2) 确认无误后正式生成
& 'C:\Env\miniconda3\envs\pmsm\python.exe' scripts\bind_simulink.py `
    --aedt models\manual\RotorySimulink_thincoder.aedt `
    --out-dir results\simulink-binding
```

产物：`<输出目录>/<design名>.slx`，一个 design 一个文件。

## 命令行参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--aedt` | 是 | Twin Builder 工程文件路径。只读解析，不会修改它 |
| `--out-dir` | 否 | 输出目录，不存在会自动创建。缺省 `.thincoder/tmp/simulink-binding` |
| `--dry-run` | 否 | 只解析并打印元件与端口，不启动 MATLAB、不生成文件。用于先确认解析结果 |
| `--config` | 否 | 配置文件路径，缺省 `config/base.yaml` |
| `--fault-expected-design` | 否 | 仅验收用：故意把期望的 design 改成别的值，模拟核验失败场景 |

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 全部块绑定并核验通过 |
| 1 | 部分块失败（其余成功），详见输出的结果表 |
| 2 | 解析阶段失败（路径不存在、文件不可读、无 `SimulinkData` 元件） |
| 3 | 引擎/环境失败（MATLAB 启动失败、输出目录无法创建） |

## 执行前的前置条件

| 项 | 要求 |
|---|---|
| Python 环境 | `C:\Env\miniconda3\envs\pmsm\python.exe`，需已装 `matlabengine`、`pywinauto`、`psutil`、`pywin32` |
| MATLAB | R2024b，`E:\Program Files\MATLAB\R2024b` |
| AnsoftSFunction | `E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b` 下需有 `AnsoftSFunction.mexw64` 与 `Sim2SimDialog.exe` 所在目录 |
| Twin Builder | 2026 R1。**建议提前打开 AEDT 并加载目标工程**——工具会触发对话框连接引擎，引擎未启动时会自动拉起 AEDT，但要等待较长时间 |

## 运行时会发生什么

工具会启动一个独立的 MATLAB 引擎进程（不影响你已打开的 MATLAB），然后对每个元件：

1. 新建空白模型，加一个 S-Function 块
2. 把块名改成 `AnsoftSFunction`，此时会**弹出 `Simplorer Link Assignment Dialog`**
3. 自动勾选 `Read link information from file`
4. 点 `Browse`，在文件对话框里填 `.aedt` 路径并确认
5. 在 design 下拉框里选中对应 design（**默认停在第一个 design，必须显式选**）
6. analysis 下拉框会自动变成该 design 的分析名
7. 点 `OK`
8. 脚本构造 `UserData` 并写回块（见下节「为什么不点 Link」）
9. 读回核验，通过后保存为 `<design名>.slx`，关闭模型

全程窗口会自动操作，**不要手动点击那个弹窗**，否则会干扰。

## 为什么不点 Link

对话框底部的信号映射表需要手工逐个点 Link 才能建立。工具没有模拟这些点击，而是直接构造
`UserData` 写回块——两者结果一致（已与你手工操作的结果逐字节比对确认）。

`UserData` 的结构：

```
DataVer:2,<aedt路径>,<project>,<design>,<analysis>,<实例名>,<输出数>,<输入数>,
<输出信号名...>,<输入信号名...>,<索引...>
```

索引规则：`range(输出信号数) + range(输入信号数)`。
「输出」指 Twin Builder 输出给 Simulink 的信号（如 `iA`），「输入」指 Simulink 送入 Twin Builder 的（如 `uA`）。
**端口数从 `.aedt` 解析得来，不写死**——6进4出、3进3出、2进1出三套均已验证。

## 产物说明

| 文件 | 内容 |
|---|---|
| `<design名>.slx` | 一个模型，内含一个已绑定的 `AnsoftSFunction` 块 |
| 块的 `Ports` | 与 `.aedt` 中的端口方向对应（Twin Builder 的输入信号数 = Simulink 块的输出数） |
| 块的 `UserData` | 绑定数据，含 `.aedt` 路径、design、analysis、实例名、信号名与索引 |

产物是**空白模型加一个块**，块与块之间、块与其它模块之间的信号线需要你在 Simulink 里自行连接。

## 常见问题

**弹窗没出现 / 等待超时**

多半是 Twin Builder 引擎未就绪。先手动打开 AEDT 加载工程，再跑工具。

**`ElementNotEnabled` 报错**

design 下拉框还没被引擎填充完。工具已内置等待与重试；若仍失败，确认 `.aedt` 能被 AEDT 正常打开。

**报告"通过"但目录里没有文件**

工具已内置落盘校验，保存后会检查文件存在，不存在判失败。若见到这种情况，说明校验本身出了问题，请报告。

**设计里同一个 design 有多个 SimulinkData 元件**

第一个用 `<design名>.slx`，第二个起自动加 `_2`、`_3`，不会覆盖已有文件。

## 当前已知限制

1. **一次只处理一个 `.aedt`**，不支持目录批量。多个工程请分别调用。
2. **不改已有 `.slx`**，只新建空白模型。
3. **不连信号线**，只放块并完成绑定。
4. **不修改 `.aedt`**，只读解析。
5. **同一模型内放多个块的问题未解决**——工具采用「一个元件一个模型」规避。若你需要单模型多块，需另行调查。

## 相关文档

| 文档 | 内容 |
|---|---|
| `docs/requirements/simulink-binding.md` | 需求：功能点 F1–F4、边界、上游约束 |
| `docs/design/simulink-binding.md` | 设计：架构、解析器、执行器、验收标准 |
| `docs/batches/2026-10-20-simulink-binding-automation.md` | 本批实施与验收记录 |

## 代码结构

```
src/data_exchange/
  models.py           数据类：BindingSpec / Port / BindingResult / UserDataFields
  aedt_parser.py      .aedt 解析：枚举 SimulinkData 元件、归属 design、端口方向
  config.py           配置读取
src/simulink_controller/
  dialog.py           窗口线程：定位弹窗、勾选、Browse、选 design、点 OK
  binder.py           MATLAB 引擎管理、双线程握手、保存
  verifier.py         读回核验与比对表
scripts/bind_simulink.py   命令行入口
tests/test_aedt_parser.py  解析器单测（11 个）
config/base.yaml           超时阈值、控件标题、宿主进程名
```
