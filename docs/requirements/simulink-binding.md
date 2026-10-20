# Twin Builder / Simulink 联合仿真绑定自动化 — 需求

## 1. 模块目标

给一个 Twin Builder 工程文件（`.aedt`），自动在新建的 Simulink 模型里生成对应的 `AnsoftSFunction` 块并完成信号绑定，替代手工逐块点击 `Simplorer Link Assignment Dialog` 的重复劳动。

## 2. 背景

Twin Builder 与 Simulink 联合仿真的绑定关系，由 Simulink 侧 `AnsoftSFunction` 块的 `UserData` 承载。官方只提供一个入口 `ShowLinkDialog(path)`（`E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b\AnsoftLinkDialog.m:9`），它只负责弹出图形对话框，不接收任何映射参数。

因此绑定必须走图形对话框。手工流程每块要点击 6 次以上，工况一多不可维护。

## 3. 功能点

### F1 从 `.aedt` 发现绑定源

给定一个 `.aedt` 路径，枚举其中所有 `ComponentDataType='SimulinkData'` 的元件，输出每个元件的：

- 所属 design 名
- 元件 `CompName`（如 `SimulinkData10`）
- 实例名 `InstanceName`（如 `MDL1`）
- 端口数、每个端口的名字与方向（`SimulinkDirection`：1 = 输入到 Twin Builder，0 = 输出到 Simulink）

**验收**：对 `models/manual/RotorySimulink_thincoder.aedt` 能解析出 1 个元件，10 个端口（`uA/uB/uC/TL` 进，`iA/iB/iC/wm/THM/Te` 出）。

### F2 批量生成已绑定的 S-Function 块

为每个发现的 `SimulinkData` 元件各生成一个独立的 `.slx`，其中包含一个 `AnsoftSFunction` 块，并完成绑定。
产物文件名取该元件的 design 名（`<输出目录>/<design名>.slx`）；每个模型里只有一个块。

**为什么一块一个模型**：同一模型里连续绑多个块时，第 2 块必然失败（`set_param` 后绑定对话框 60 s 不出现），已稳定复现 3 次；
改成每块独立模型后三套 design 全部成功。根因未定位，故按实测可用的形态定需求。

**验收**：跑一次后输出目录下有 3 个文件 `MatlabConnect.slx` / `Simplorer1.slx` / `Simplorer2.slx`，每个文件含 1 个 `AnsoftSFunction` 块；
每个块的 `UserData` 以 `DataVer:2,` 开头、包含正确的 `.aedt` 路径 / design 名 / 实例名，且末尾索引序列不是全 `-1`。
`Parameters` 不作判据：实测点 OK 后读回为空串，而已绑定成功的旧模型里是 `-1`，取值不稳定。

### F3 绑定结果核验

每个块生成后，读回 `Parameters` 与 `UserData`，与 F1 解析出的期望值逐字段比对，报告一致或差异。

**验收**：核验结果打印每个块的字段比对表；不一致时明确列出哪个字段、期望值、实际值。
比对字段为 `UserData` 前缀、`.aedt` 路径 / design / 实例名三个子串、末尾索引序列（构造规则 `range(输出端口数) + range(输入端口数)`）。

### F4 失败可见

任一环节失败（`.aedt` 解析失败、弹窗未出现、Browse 对话框操作失败、绑定后参数不符），不静默跳过，输出失败原因与所在步骤。

**验收**：故意给一个不存在的 `.aedt` 路径，程序报错并指出是解析阶段失败，退出码非 0。

## 4. 边界（明确不做）

- **不做信号连线**：只在空白模型里放置块，块之间的信号线由人工在 Simulink 里连。
- **不做同名文件覆盖**：输出目录里已有同名 `.slx` 时报错停下，不重写已有模型。
- **不做反向操作**：不允许从 Simulink 块反推并改写 `.aedt`。
- **不做已有的 `.slx` 增删块**：本期只新建空白模型。
- **不驱动点击 `Link` / `Autolink` 按钮**：映射改由脚本直接构造并写入 `UserData`，索引按「输出端口数 + 输入端口数」生成，绕开逐项 UI 点击。
  依据：实测勾选并选定 design 后点 OK，`UserData` 末尾索引全为 `-1`，映射并未填满；用户实测「Autolink 没有用」。
- **不点 `NEW` / `DELETE` 按钮**：两者是对话框内的清单维护操作，与绑定无关，脚本不触碰。
- **不修改 `.aedt` 文件内容**：只读解析。
- **不处理 Maxwell / Motor-CAD 链路**：仅 Twin Builder ⇄ Simulink。

## 5. 依赖

| 依赖 | 版本 / 位置 | 用途 |
|---|---|---|
| MATLAB | R2024b，`E:\Program Files\MATLAB\R2024b` | 宿主，`matlab.engine` |
| `AnsoftSFunction` | `E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b` | 绑定对话框提供方 |
| AEDT / Twin Builder | 2026 R1 | 提供 `.aedt` 工程文件 |
| Python | `C:\Env\miniconda3\envs\pmsm\python.exe` | 驱动脚本 |
| pywinauto | 0.6.9（已装） | 操作图形对话框 |

## 6. 上游约束（实测确认，构成设计前提）

| 约束 | 证据 |
|---|---|
| `ShowLinkDialog` 只有一个 `const char*` 参数，不接收映射 | `AnsoftSFunction.h:17`；`libfunctions` 实测只返回 `ShowLinkDialog` |
| 改 `FunctionName` 为 `AnsoftSFunction` 会阻塞并弹出模态对话框 | 实测：`set_param` 不返回，直到窗口关闭 |
| 端口名（`InputSignalNames`/`OutputSignalNames`）只读，脚本无法设置 | 实测 `set_param` 报「参数为只读」 |
| `UserData` 与 `Parameters` 可写 | 实测写入成功并读回 |
| 对话框勾选 `Read link information from file` 只负责读入 `.aedt` 清单，不建立映射 | 实测点 OK 后 `UserData` 末尾索引全为 `-1`；用户实测「Autolink 没有用」，须逐个点 Link |
| `.aedt` 路径行是 Static（只读），只能经 `Browse` 选择 | 实测控件类型为 `Static` |
| 两个下拉框：design 框选文件后读入全部 design、但默认停在第一个，须显式选择；analysis 框随 design 自动变为唯一分析 | 实测 design 框 4 项，默认 `Original Secondary-36`；`select('MatlabConnect')` 后 analysis 框为 `TR` |
| 弹窗宿主是独立进程 `Sim2SimDialog.exe`，不在 MATLAB 进程组内 | 实测 `EnumWindows` + `GetWindowThreadProcessId`：祖先链 `Sim2SimDialog.exe` <- `MATLAB.exe` <- `python.exe` <- `pwsh.exe` |

## 7. 使用形态

命令行：给定 `.aedt` 路径与输出目录，一次生成完毕。每个元件产出一个 `<design名>.slx`。

```
python scripts/bind_simulink.py --aedt <path.aedt> --out-dir <目录>
```

产物：`<目录>/<design名>.slx`，每个文件含一个已绑定的 `AnsoftSFunction` 块。目录不存在则自动创建；
该目录已含同名 `.slx` 时该块报错，不覆盖。

可选开关 `--dry-run`：只执行 `.aedt` 解析并打印发现的元件与端口，不启动 MATLAB 引擎、不生成 `.slx`。
用途是让 F1 可以脱机验收——解析是纯文本处理，为了验证它而拉起整个 MATLAB 引擎不划算。

```
python scripts/bind_simulink.py --aedt <path.aedt> --dry-run
```

## 8. 待定项

无。所有影响实现的判断已由实测确定。
