# Twin Builder ⇄ Simulink 绑定自动化 — 设计

> 需求来源：`docs/requirements/simulink-binding.md`（本文逐条对应其 F1–F4）
> 证据分级：**实测** = 本机跑过或有文件/代码可读；**推断** = 由实测推得，未单独验证。

## 1. 方案与理由

**一句话方案**：Python 主进程解析 `.aedt` 得到绑定清单 → 启动两个协作体（MATLAB 引擎线程 + pywinauto 窗口线程）→ **每个元件各建一个独立 `.slx` 模型**，模型内走「建块 → 触发弹窗 → 勾选 Read link information from file → 选 `.aedt` → OK」→ 读回参数核验 → 保存并关闭该模型。

**为什么一个元件一个模型**（实测裁决）：同一模型里连绑多个块会失败。正式实现一个模型装三块时，第 1 块成功、第 2 块 `set_param` 后对话框 60 s 不出现、第 3 块又成功，稳定复现 3 次；
探针改成每块各起一个新模型，三套 design（`MatlabConnect` 6 进 4 出 / `Simplorer1` 3 进 3 出 / `Simplorer2` 2 进 1 出）连续全部成功。
引擎复用、窗口进程残留、控件 API、`UserData` 字段顺序四个假设均已被探针逐项排除（同引擎连跑两次两次都过），故结论是**同模型内多次绑定会留状态残留，独立模型是唯一的隔离手段**。

**为什么必须双线程而不是一条直线**：`set_param(blk,'FunctionName','AnsoftSFunction')` 是同步阻塞调用，弹窗不关闭它永不返回（需求 §6 实测，探针卡 420 秒超时）。
同一条线程里调完 `set_param` 就再也执行不到 pywinauto 的代码，所以「触发弹窗」和「操作弹窗」必须在两个可并行推进的执行体里。

**为什么不绕开弹窗**：官方入口只有 `ShowLinkDialog(path)` 一个函数（`E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b\AnsoftSFunction.h:17`，实测读文件确认签名只有一个 `const char*`），
端口名参数 `InputSignalNames`/`OutputSignalNames` 只读（需求 §6 实测），`ctypes` 直加载 DLL 缺 `libmx/libmex/libeng`（需求 §10）。
三条路都堵死，图形弹窗是唯一写入通道。

**最近先例**：项目内无同类先例（`docs/design/` 本批新建，此前无设计文档）。
对齐依据取 `AGENTS.md` 的既有约定：控制器在 `src/`、入口脚本在 `scripts/`、测试在 `tests/`、配置在 `config/`，本文照此划分，不另立目录形态。

`help/repos/` 下三个已有工程的目录与入口形态也勘察过（`pymotorcad/`：`src/`+`examples/`+`samples/`+`tests/` 单包形态；
`pyaedt-mcp/`：MCP server 单进程入口；`matlab-agentic-toolkit/`：MATLAB 插件结构），均未采用——它们是「一个库/一个 server」的发布单元，
而本项目的发布单元是本机的命令行脚本 + 控制器包，边界是外部工具（Motor-CAD / AEDT / Simulink）而非库 API，套用会多出一层无收益的包结构。

**公开资料勘察**：已查 `help/ansys-help-topics/` 下 Twin Builder 主题的快照（25 个主题之一，章节「Simplorer Link Assignment Dialog」存在）、
`help/repos/pyaedt-mcp/`（MCP server 源码，与本任务的对话框操作无关，**无相关内容**）、`help/repos/matlab-agentic-toolkit/`（MATLAB agent 工具集，**无相关内容**）。

**勘察到但按边界不用**：`help/ansys-help-topics/` 下 Twin Builder 主题快照的「Simplorer Link Assignment Dialog」章节（第 `23149-23153` 行）官方流程含
「勾选 Read link information from file → Browse 选 `.aedt` → 用 Link / Autolink 按钮建立信号连线」；
其中 Link / Autolink 一步按需求边界主动跳过（需求 §4「不做信号连线」，设计 §7）——实测勾选并选定 design 后点 OK，`UserData` 末尾索引全为 `-1`，映射并未填满，
且用户实测「Autolink 没有用」。故改为：脚本不点 Link，改为直接构造 `UserData` 写回（§4.3），绕开逐项 UI 点击。这是有意的取舍，不是漏查。

## 2. 总体架构

### 2.1 三段流水线

```
scripts/bind_simulink.py          ← 命令行入口，只做参数解析与退出码
        │
        ├─ 段① src/data_exchange/aedt_parser.py     .aedt 文本 → BindingSpec 列表
        ├─ 段② src/simulink_controller/binder.py     MATLAB 引擎 + pywinauto 双线程绑定
        └─ 段③ src/simulink_controller/verifier.py   读回 Parameters / UserData 逐字段比对
```

段与段之间只传数据对象（`BindingSpec` / `BindingResult`），不共享句柄——任一段可单独跑测试。

**模型粒度**：一个 `BindingSpec` 对应一个模型文件 `<输出目录>/<design名>.slx`，模型内只有一个块。
模型生命周期 = 新建 → 建块绑定 → 核验 → 保存 → 关闭，下一块另起新模型（理由是上节实测裁决）。
因此 `--out-dir` 的语义是**输出目录**，不是单个模型文件（命名规则见 §4.5）。

### 2.2 三个执行体与它们的同步

| 执行体 | 载体 | 负责 |
|---|---|---|
| 主线程 | Python 主线程 | 解析、调度、核验、退出码 |
| MATLAB 引擎 | `matlab.engine.start_matlab(background=True)` 返回的 `FutureResult` | 建块、`set_param` 触发弹窗、读回参数、关窗后的收尾 |
| 窗口线程 | `threading.Thread` + `pywinauto.Application(backend='win32')` | 定位对话框、勾选、Browse、OK |

**同步机制（本设计的核心）**——两段握手，全部基于「可轮询的状态 + 超时」，不用无界 `join()`：

1. **触发**：主线程把块名投进队列，MATLAB 引擎线程执行 `set_param(blk,'FunctionName','AnsoftSFunction')`，随即阻塞。
2. **窗口出现判据**：窗口线程以 200 ms 间隔轮询顶层窗口，判据是**三条件同时成立**——
   ① 窗口类名 `#32770`；② 标题为 `Simplorer Link Assignment Dialog`；
   ③ 该窗口的宿主进程名为 `Sim2SimDialog.exe`，且其祖先进程链中存在本会话拉起的 `MATLAB.exe`。
   条件③的依据（实测 `EnumWindows` + `GetWindowThreadProcessId`）：弹窗宿主是 **`Sim2SimDialog.exe` 独立进程**，不在 MATLAB 进程组内——
   祖先链为 `Sim2SimDialog.exe` <- `MATLAB.exe` <- `python.exe` <- `pwsh.exe`。它不属 MATLAB 进程组，但祖先链必含本会话的 `MATLAB.exe`，故判据改看祖先链。
   条件①+② 已足以互相排除同机其它模态框；③ 再防旧会话或本机其它进程拉起的同名窗口。
3. **交接**：窗口线程完成勾选与文件选择后点 OK，窗口销毁。
4. **引擎解阻**：主线程检测「窗口已消失」后，`FutureResult` 自然返回；随即读回 `Parameters` / `UserData` 供核验（判据见 §4.3，`Parameters` 不作判据）。

`set_param` 阻塞时 pywinauto 如何接手：`set_param` 跑在 **MATLAB 引擎的子进程**里，引擎调用本身以 `background=True` 异步返回句柄给 Python 主线程；
主线程不被阻塞，窗口线程也不被阻塞——三者里只有 MATLAB 的内部脚本线程在等窗口，而那正是我们希望的等待。

### 2.3 三种异常与超时

| 异常 | 检测判据 | 处理 |
|---|---|---|
| 弹窗未出现 | 触发后 `WINDOW_WAIT_S`（默认 60 s）内轮询未命中窗口判据 | 记录「步骤=触发弹窗，原因=窗口未出现」；尝试 `Cancel` 兜底；该块判失败，继续下一块 |
| 弹窗出现但不响应 | 窗口已命中，但单步操作（勾选/点 Browse/点 OK）抛 `pywinauto` 超时或控件不可用 | 记录具体控件名；按 Esc 关窗释放引擎，该块判失败 |
| 弹窗卡死 | 点击 OK 后 `CLOSE_WAIT_S`（默认 120 s）内窗口未销毁 | 记录「步骤=关窗」；`process.kill` 掉该 MATLAB 引擎并从新引擎继续下一块（该块的模型文件此时未必存在，见 §4.5） |

三种情况都写进 `BindingResult.status`，绝不静默跳过（对应 F4）。

## 3. `.aedt` 解析器设计

### 3.1 文件结构的实测事实

实测试例 `models/manual/RotorySimulink_thincoder.aedt`（UTF-8 文本，`DesignInfo` 段收于第 70312 行 `$end 'ProjectPreview'`）中：

- 元件库定义在 `$begin 'SimulinkData'` … `$end 'SimulinkData'` 段内（第 9919–10007 行），
  带 `ComponentDataType='SimulinkData'`（第 9949 行）与 `SimulinkName0..9` / `SimulinkDirection0..9`（第 9956–10003 行）。
- 实际放置的实例在 `$begin 'Compinst'` 段内（第 49461 行起）：`ID='206'`（第 49462 行）、
  `CompName='SimulinkData10'`（第 49464 行）、`TextProp('InstanceName','OD','',CB='InstanceName','MDL1')`（第 49469 行）。
- **design 归属走 Refdes，不走 `Compinst` 的 ID**：`$begin 'Instance'` 段（第 57663 行）有 `DesignEditor='MatlabConnect'`（第 57664 行）、
  `ID='181'`（第 57665 行），其 `Refdes('206', 'MDL1')`（第 57679 行）把元件 ID 206 映射到实例名 `MDL1`。
  即：`Compinst` 的 `ID` = Refdes 的第一个参数 → 命中该 `Instance` 段的 `DesignEditor`。
  该段落实测仍能对上的另一条：`DesignEditor='RotorySimulink1_ckt'`（第 50660 行）/ `ID='178'`（第 50661 行）。
- 4 个 design 名的 `DesignName=` 逐行在 `DesignInfo` 段内（第 68560 / 68682 / 69349 / 69646 行）。
- 分析（TR）名在 `DesignInfo` 的 `'Nominal Setups'[1: 'TR']`（第 69353 行，属第 69349 行的 `MatlabConnect`）。

**推断（未验证）**：一个 `.aedt` 里存在多个 `Instance` 段时，Refdes 只在所属段内有效——本设计按段内查表实现，
若同一 ID 在多段出现，取与 `SimulinkModelName` 一致的段并记录全部候选以便人工核对。

### 3.2 定位规则

1. 逐行扫描，维护 `$begin 'X'` / `$end 'X'` 的栈。
2. 进入 `Compinst` 帧时记录 `CompName` / `InstanceName` / `ID`。
3. **判据是子树，不是同帧**：在 `Compinst` 帧**及其全部嵌套子帧**内出现 `ComponentDataType='SimulinkData'` ⇒ 判为 SimulinkData 元件。
   实现上是「进入 `Compinst` 帧后置标志，直到配对 `$end 'Compinst'` 之前，任一层级出现该字段即命中」，不能写成「栈顶帧名 == Compinst」。
   实测依据：`models/manual/RotorySimulink_thincoder.aedt:49461` 是 `$begin 'Compinst'`，`:49472` 是嵌套的 `$begin 'CompData'`，
   `:49473` 才是 `ComponentDataType='SimulinkData'`——目标字段在第 2 层嵌套内，按同帧严格相等会零命中。
4. design 归属：在该实例所属的 `Instance` 段内按 `ID` 查 `Refdes('<id>', '<instance>')`，取同段的 `DesignEditor`。
5. 端口表优先取该帧**子树内**的 `SimulinkName<i>` / `SimulinkDirection<i>`（`i` 从 0 到 `SimulinkVectorSize-1`）；实测样本实例帧内已完整（`:49480-49529`），主路径可用。
   若实例子树内无端口行（实例精简存放），回退到 `$begin 'SimulinkData…'` 库定义段按 `SimulinkModelName` 匹配，**多段命中时取该名字的最后一个匹配段**。
   回退路径本批无实样（唯一被测 `.aedt` 的实例帧自带端口行），规则未实测，已登记 §10 未决项。

### 3.3 数据结构

```python
@dataclass(frozen=True)
class Port:
    index: int
    name: str          # uA / iA …
    direction: int     # 1 = 输入到 Twin Builder，0 = 输出到 Simulink

@dataclass(frozen=True)
class BindingSpec:
    aedt_path: Path    # 绝对路径
    project: str       # .aedt 文件名去扩展名
    design: str        # DesignEditor 名
    analysis: str      # Nominal Setups 首项
    comp_name: str     # SimulinkData10
    instance: str      # MDL1
    vector_size: int
    ports: list[Port]
```

### 3.4 边界

| 情况 | 行为 |
|---|---|
| 0 个 SimulinkData 元件 | 报错退出码 2，信息含「解析阶段：未发现 ComponentDataType='SimulinkData' 的元件」 |
| 1 个 | 正常出 1 个 `BindingSpec`，即 1 个 `<design名>.slx` |
| 多个 | 全部生成，互不覆盖；块名 `{instance}`（重名时追加 `_2`、`_3`） |
| 某元件找不到 design 归属 | 该元件判失败并记录 ID，其余照常出结果 |

## 4. 绑定执行器设计

### 4.1 单块动作序列

一个块从头到尾在一张**本块专用的新模型**上完成，模型名 = 本块的 `design` 名（命名见 §4.5）。

| 步 | 动作 | 执行体 |
|---|---|---|
| 0 | `new_system('<design名>')` —— 本块专用空白模型；同名模型已开则先 `close_system(..., 0)` 再建 | MATLAB 引擎 |
| 1 | `add_block('simulink/User-Defined Functions/S-Function', '<design名>/'+blk)` | MATLAB 引擎 |
| 2 | `set_param(blk,'FunctionName','AnsoftSFunction')` （**阻塞，弹窗出现**） | MATLAB 引擎（异步提交） |
| 3 | 等窗口判据命中（§2.2 条件①②③） | 窗口线程 |
| 4 | 勾选：`child_window(title='Read link information from file', class_name='Button').check_by_click_input()` | 窗口线程 |
| 5 | 点 `Browse`：`child_window(title='Browse', class_name='Button').click_input()`（见 §4.2） | 窗口线程 |
| 6 | 文件对话框填 `.aedt` 绝对路径并确认（见 §4.2） | 窗口线程 |
| 7 | 选 design：第一个 `ComboBox`（`found_index=0`）`.select(<design名>)` | 窗口线程 |
| 8 | 第二个 `ComboBox`（analysis）不操作：选完 design 后自动变为该 design 的唯一分析 `TR` | 窗口线程 |
| 9 | 点 `OK`：`child_window(class_name='Button', title='OK').click_input()` | 窗口线程 |
| 10 | 等窗口销毁，`set_param` 返回 | 主线程轮询 |
| 11 | 读回 `UserData`（此时末尾索引全为 `-1`） | MATLAB 引擎 |
| 12 | 构造完整 `UserData` 并 `set_param(blk,'UserData',<构造串>)` 写回（构造规则见 §4.3） | MATLAB 引擎 |
| 13 | 读回核验（判据见 §4.3） | MATLAB 引擎 |
| 14 | `save_system('<design名>', '<输出目录>/<design名>.slx')`（见 §4.5） | MATLAB 引擎 |
| 15 | `close_system('<design名>', 0)` —— 关模型且不弹保存提示；下一块从步 0 另起新模型 | MATLAB 引擎 |

**控件定位的事实（实测）**：对话框是 `Desktop(backend='win32').window(title='Simplorer Link Assignment Dialog', class_name='#32770')`。
`print_control_identifiers` 显示的 `Read link information from fileCheckBox` 是 pywinauto 生成的显示别名，**不是真实 `auto_id`**：
按 `child_window(auto_id='Read link information from fileCheckBox')` 找不到，必须按 `title` + `class_name='Button'` 定位。

**勾选必须走真实鼠标事件（实测）**：`check()` 只发 `BM_SETCHECK` 消息改状态位（`pywinauto/controls/win32_controls.py:162`），
状态位显示已勾选，但官方对话框不响应后续逻辑——Browse 点了也没反应。`check_by_click_input()` 发真实鼠标事件，一切正常。
用户侧旁证：手动点控件文字也能正常弹出文件对话框，说明该对话框监听真实鼠标消息。

**`Browse` 按钮不要判 `is_enabled()`（实测）**：未选文件时返回 `False`（灰色），但 `click_input()` 有效，文件对话框照常弹出。
用户实测口径：「Browse 灰色是正常态，只有选过文件之后才变成换文件可用」。故判据取「点击后文件对话框出现」，不取按钮可用状态。

参数可写性实测：`UserData` 与 `Parameters` 可写并读回成功（需求 §6）；端口名只读，故不由脚本写入。

**design 必须显式选择（实测）**：对话框第一个下拉框默认停在文件里的**第一个** design，不会自动跳到目标。
实测该 .aedt 有 4 个 design（`Original Secondary-36` / `MatlabConnect` / `RotorySimulink1_ckt` / `ECE`），`select('MatlabConnect')` 后 `window_text()` 变为 `MatlabConnect`。
选错 design 会绑到别的工程分支上，故选择后必须读回 `window_text()` 与期望比对，不符即判该块失败。

### 4.2 Browse 原生文件对话框（已实测）

点 `Browse` 弹出的是 Windows 原生 `#32770` 文件对话框，实测 0.2 秒内出现，无延迟。已验证的操作链：

```python
file_dlg = Desktop(backend='win32').window(title='打开', class_name='#32770')
file_dlg.child_window(class_name='Edit', found_index=0).set_edit_text(str(aedt_abs_path))
file_dlg.child_window(class_name='Button', title_re='打开.*').click_input()
```

三条实测要点：

1. **文件名栏取 `class_name='Edit', found_index=0`**——对话框里 `ComboBoxEx32` 内嵌的 Edit 是文件名栏，`set_edit_text()` 有效，路径正常回填到主弹窗。
2. **确认按钮用 `title_re='打开.*'`**——按钮实际标题带全角括号（`打开(&O)`），精确匹配 `打开(O)` 匹配不到。
3. **不要遍历 `Desktop.windows()` 再调 `child_window()`**——列表元素是 `DialogWrapper`，没有 `child_window` 方法；直接按标题建对话框对象再找控件。

**失败兜底（实测可用）**：`title_re` 也匹配不到确认按钮时，改用 `Edit.set_focus()` + `send_keys('{ENTER}')`。
兜底仍失败则该块判失败（F4），**不得**回退到手工点击的静默放行。

**前置条件**：选中 `.aedt` 后若 Twin Builder 引擎未就绪，官方会自动拉起 AEDT，需要等待一段时间。
本批验收按「提前打开 AEDT 并加载工程」执行；自动拉起作为已知行为记录，不纳入本批判据。

### 4.3 绑定成功判据

读回 `UserData`，三条全部满足才算成功：

1. 以 `DataVer:2,` 开头
2. 文本包含 `.aedt` 绝对路径、design 名、instance 名三个子串
3. 末尾索引序列**不是**全 `-1`（全 `-1` 说明对话框只选了文件、没有真正链接）

**`Parameters` 不作判据（实测）**：脚本点 OK 后读回 `Parameters` 是空串 `''`；用户已绑定成功的旧模型 `RotaryMaxwell1.slx` 里却是 `'-1'`。
取值不稳定，用它会误判失败，故从判据中移除。

**索引序列的构造规则（实测 + 用户截图确认）**：`UserData` 末尾是端口配对索引，前段为输出配对、后段为输入配对。
对话框里上组 `SIMPLORER-OUT` 与 `SIMULINK-OUT` 严格同行配对（该样本 6 对，`Node[0] <- iA` … `Node[5] <- Te`），
下组 `SIMULINK-IN` 与 `SIMPLORER-IN` 严格同行配对（该样本 4 对，`Node[0] -> uA` …，下组重新从 `Node[0]` 起）。
故构造规则为：

```
索引序列 = list(range(输出端口数)) + list(range(输入端口数))
```

输出端口数 / 输入端口数取自段①解析结果（`SimulinkDirection`：1 = 输入到 Twin Builder，0 = 输出到 Simulink），**不得写死**。
实测验证：`out_n=6, in_n=4` 生成 `[0,1,2,3,4,5,0,1,2,3]`，与手工点完 Link 的 `UserData` 逐字节一致（长度 180）。

**写回方式（实测）**：直接 `set_param(blk,'UserData',构造串)` 调用，不经 `eval` 字符串；读回与手工结果逐字节一致。
写入后 `save_system` 再 `close_system` + `load_system`，`UserData` 与 `Ports`（4 进 6 出）均保持不变——即落盘不丢绑定状态，断点后才按 §4.1 步 15 关模型。

**不解析 `UserData` 的其余字段序**——除索引序列外，字段语义仍是从单一实样反推的，不作设计前提。

### 4.4 多块批量的隔离手段：一块一模型

批量 = 对 `BindingSpec` 列表逐个跑 §4.1 的全序列，**每块从步 0 新建自己的模型、步 15 关闭它**。块与块之间不共享模型、不共享块句柄，也**不靠断言某个控件状态来隔离**。

为什么必须是模型级隔离（实测）：同一模型内连续绑多个块时，第 2 块的 `set_param` 后对话框不出现（60 s 超时）；
换成一块一模型后同样的三套 design 全部通过。引擎复用、`Sim2SimDialog.exe` 残留、控件 API、字段顺序四个假设均已被探针排除。

剩下的两条块间干扰，仍按原口径处理：

1. **design 必须显式选择**：对话框默认停在文件里的第一个 design，故每块走 §4.1 步 7 的 `select(<design名>)` 并读回 `window_text()` 比对；不读回就会静默绑到错误的 design。
2. **引擎异常时整引擎重启**（§2.3 卡死处理）：重启后当前块重建新模型重跑该块；已落盘的模型不受影响（§4.5）。

同一个 design 下若有多个 SimulinkData 元件，它们的模型名会撞——见 §4.5 的命名去重。

### 4.5 每块的保存、关闭与命名

块是 `add_block` 加在 MATLAB **内存模型**里的，不落盘就只存在于引擎进程内。§2.3 规定弹窗卡死时 `process.kill` 掉引擎再重建，
重建后内存模型没了——若不保存，本块结果就丢了。故一块绑定并通过 §4.3 核验后，立即 `save_system` 到自己的文件，再 `close_system` 关模型。

- **产物命名：`<输出目录>/<design名>.slx`**。选 design 名是因为它在 `.aedt` 内唯一、用户能直接对上是哪套（实测三个：`MatlabConnect` / `Simplorer1` / `Simplorer2`）。
- **`--out-dir` 是输出目录**，默认 `.thincoder/tmp/simulink-binding`（该目录已被 `.gitignore` 忽略，§5.2）；目录不存在则建。
- **文件名安全**：目标文件名取 design 名，但把 Windows 非法字符 `< > : " / \ | ? *` 与控制字符换成 `_`，并去掉结尾的 `.` 与空格（Windows 会默默吃掉结尾点）。
  MATLAB **模型名**另由文件名变来：非标识符字符换成 `_`，首字符不是字母时加前缀 `m_`（`binder.py:183` 现有实现照用）。
  转换只影响 MATLAB 内的模型名，落盘文件名保持 design 原形（除非含非法字符）。
- **撞名去重**：同一 design 下有多个元件时（同一 `InstanceName` 在 `.aedt` 里会被 Simulink 判为一个模型），
  第二个起在文件名后加 `_2`、`_3`，并写进结果表——不静默覆盖。实测样本一个 design 只有一个元件，本路径无实样，登记 §10。
- **旧文件**：目标文件已存在即报错（`EngineError`，该块判失败），不覆盖。理由是边界「不修改已有 `.slx`」（§7）；用户要重跑就清目录。
- 保存放进异常保护：`save_system` 抛错（路径不可写、目录无权限、文件被其它 MATLAB 会话占用）时，该块记失败、原因写「步骤=保存，原因=<异常文本>」，关闭模型后继续下一块。
- 保存失败不回退已完成的绑定状态：块在内存里仍是绑好的，但不算成功——F2 的通过判据是落盘后的 `.slx` 读回值，不是内存读数。
- **逐块保存、逐块关闭**：不要攒到批末——攒批时任何一次 kill 或卡死都会连带丢掉本模型内尚未落盘的块。

## 5. 目录结构与 git 策略

### 5.1 目录划分

```
src/
├── data_exchange/          # 跨工具数据：aedt_parser.py、models.py（BindingSpec/Port/BindingResult）
├── simulink_controller/    # 绑定域：binder.py（MATLAB 引擎线程）、dialog.py（pywinauto 窗口线程）、verifier.py
└── motorcad_controller/    # 预留，本批不建（Maxwell/Motor-CAD 链路不在本期）
scripts/
└── bind_simulink.py        # 命令行入口
tests/
└── test_aedt_parser.py     # 本批唯一单测面：纯文本解析，可脱机跑
config/
└── base.yaml               # 超时阈值、块路径模板
.thincoder/tmp/
└── simulink-binding/       # 缺省输出目录：每块一个 <design名>.slx（已被 .gitignore 忽略）
docs/
├── requirements/           # 需求档（主 agent 笔）
├── design/                 # 设计档（本文件）
└── batches/                # 批次记录
```

命名理由：`src` 按「工具边界」分目录，一个外部工具一个控制器目录——与 `AGENTS.md` 已规划的目录形态一致，后续加 Maxwell 不必挪动既有文件。

### 5.2 `.gitignore` 规则清单

| 规则 | 为什么忽略 |
|---|---|
| `help/ansys-help-topics/` | Ansys 官方帮助的 md 快照，711 文件 66.8 MB，可由 AEDT 帮助重新导出，属生成物 |
| `help/repos/` | 三个公开仓库的克隆，1521 文件 75.5 MB，且各自带 `.git`（嵌套仓库会让外层 git 误判为子模块）；克隆地址内联在 `help/README.md` 目录总览的仓库条目下（§5.3），不放在被忽略的目录里 |
| `.thincoder/tmp/` | 探针脚本临时区，随时可清 |
| `*.aedtresults/` | AEDT 求解产物目录（实测 `models/manual/RotorySimulink_thincoder.aedtresults/` 内为 semaphore、`temp/`） |
| `*.aedt.lock` | AEDT 打开时写的锁文件（实测 `models/manual/RotorySimulink_thincoder.aedt.lock`），运行期产物 |
| `*.asol_priv` / `*.asol` / `*.semaphore` | AEDT 求解会话/信号量文件（实测于 `.aedtresults/` 下） |
| `*.sdb` / `*.sml` / `*.sst` / `*.sstr` | Twin Builder 求解器中间件与数据文件 |
| `*.msh` / `*.fld` | 网格与场结果文件（Maxwell 阶段产物，同规则一次性覆盖） |
| `*.aedtresults*` 之外：`*.reg` / `*.log` / `logfile` | AEDT 运行日志（实测 `models/manual/logfile`） |
| `*.mldatx` | Simulink 仿真数据存档（实测 `models/manual/New_Session.mldatx`，16 MB） |
| `slprj/` | Simulink 增量编译缓存目录 |
| `*.slxc` | Simulink 模型编译缓存 |
| `*.slx.autosave` / `*.slx.r20*` | Simulink 自动保存与旧版备份 |
| `*.sph` | Twin Builder 求解配置残留（实测 `models/manual/RotorySimulinkECE1.sph`） |
| `__pycache__/` / `*.pyc` / `.pytest_cache/` | Python 运行缓存 |
| `results/` | 批次结果归档，属生成物 |
| `plans/` | 工作计划草稿区 |

**提交什么**：`models/` 只提交源文件——`.aedt`（工程）、`.slx`（模型）、`.m`（脚本）、`.mot`（模板）。
理由：源文件是重建实验的输入，体积可控（实测 `.aedt` 3.3 MB、`.slx` 281 KB）；运行产物可重新生成，提交只会让仓库随时间膨胀，且二进制产物每次求解都变，diff 无意义。

### 5.3 `help/README.md` 的仓库登记方式

`help/repos/` 整体被忽略，克隆地址写进 `help/README.md`（该文件本身进版本库，地址才不会随目录一起丢失）。
写法是**内联在目录总览的代码块里**，不另起登记段：`repos/` 分支下每个仓库条目一行，紧跟一行上游 URL。

```
├── repos/                            ← GitHub 仓库克隆（shallow；本目录被 .gitignore 忽略，不纳入版本库）
│   ├── pymotorcad/                   ← ansys/pymotorcad main(0.9.dev0)；examples/ + samples/ + tests/ 示例齐全
│   │   └─ https://github.com/ansys/pymotorcad.git
```

这是 `help/README.md:12-18` 的现有形态（其余两个仓库 `pyaedt-mcp`、`matlab-agentic-toolkit` 同形）。要点三条：

1. 每个仓库条目下带一行上游 URL，克隆即 `git clone <URL> help/repos/<仓库名>`，无需另写命令块。
2. `repos/` 行尾注明「本目录被 .gitignore 忽略，不纳入版本库」，让读者一眼知道这份克隆不进外层仓库。
3. **不新增独立登记段、不列 URL 表格、不写 `git clone --depth 1` 命令块**——目录索引处已写全，同一事实在文件内出现两处必然漂移；克隆深度由使用者按需决定。

本次对 `help/README.md` 的动作是**在目录总览内补仓库 URL 一行与 `repos/` 行的忽略说明**，不追加段落。

## 6. 错误处理

### 6.1 错误信息要素

每条失败信息固定四段：`阶段 | 对象 | 判据 | 实测值`。例：
`绑定 | Blk=MDL1 | 窗口 60s 内未出现 | 已轮询 300 次，命中 #32770 窗口 0 个`。
四段齐全才能定位是哪一段崩的，缺一段的报错等于没报。

### 6.2 退出码

| 码 | 含义 |
|---|---|
| 0 | 全部块绑定并核验通过（每块各自的 `.slx` 已落盘） |
| 1 | 部分块失败（其余成功），详见结果表（含每块的输出文件路径） |
| 2 | 解析阶段失败（路径不存在、无 SimulinkData 元件、文件不可读） |
| 3 | 引擎/环境失败（MATLAB 启动失败、pywinauto 不可用、输出目录无法创建） |

### 6.3 F1–F4 对应的验收命令

| 需求 | 验收命令 | 通过判据 |
|---|---|---|
| F1 | `python scripts/bind_simulink.py --aedt models/manual/RotorySimulink_thincoder.aedt --dry-run` | 输出 1 个元件 `SimulinkData10`/`MDL1`，10 端口：`uA,uB,uC,TL` 方向 1，`iA,iB,iC,wm,THM,Te` 方向 0 |
| F2 | `python scripts/bind_simulink.py --aedt models/manual/RotorySimulink_thincoder.aedt --out-dir .thincoder/tmp/simulink-binding` | 每个元件各生成一个 `<输出目录>/<design名>.slx`，每个文件里只有 1 个块。实测样本 3 个元件 ⇒ `MatlabConnect.slx` / `Simplorer1.slx` / `Simplorer2.slx`；每块 `UserData` 满足 §4.3 三条判据 |
| F3 | 同上，读回表 | 打印每块字段比对表（字段 / 期望 / 实际 / 结论），全一致时退出码 0 |
| F3（不一致） | 同上，把期望值人为改错一处（如把期望的 `MatlabConnect` 改成 `MatlabConnect_x`） | 比对表该行「结论」列判不符且四列齐全（字段 / 期望 / 实际 / 结论），退出码 1（§6.2「部分块失败」） |
| F4 | `python scripts/bind_simulink.py --aedt models/manual/_not_exist.aedt --out-dir <任意目录>` | 报错含「解析|路径不存在」，退出码 2 |
| F4（绑定后参数不符） | 同 F3 不一致场景，不注入解析错误 | 该块 `status` 记失败、原因走四段式（阶段=核验），该块不计通过，退出码 1——参数不符不得静默算通过 |

`--dry-run` 是本次新增的开关，只为让 F1 可独立验收（不进 §7 边界之外的任何功能）。

模型粒度的另两条验收读数：① 模型文件个数 = 元件个数（实测样本 3 = 3），且文件名取自 design 名；② `--out-dir` 下已存在同名文件时该块报「输出模型已存在」（不覆盖，§4.5）。

## 7. 边界（不做）

- 不连信号线；不修改已有 `.slx`；不点 `Link` / `Autolink` / `NEW` / `DELETE`；不改写 `.aedt`；不碰 Maxwell / Motor-CAD；无图形界面。
  其中不点 Link / Autolink 与官方帮助的对话框流程有差（帮助要求用它建立信号连线）：该步骤已勘察，按需求边界主动跳过——
  链路改由脚本直接构造并写回 `UserData`（§4.3）完成，绕开逐项 UI 点击；理由见 §1。

## 8. 受影响文件清单

| 文件 | 现状 | 本次动作 | 预估行数 |
|---|---|---|---|
| `docs/design/simulink-binding.md` | 存在，现 416 行 | 已写入一块一模型形态（§1 / §2.1 / §4.1 / §4.4 / §4.5 / §5.1 / §6.2–§6.3 / §8）；后续仅随实现回填 §10 | 现 416 → 下一轮不限 |
| `docs/batches/2026-10-20-simulink-binding-automation.md` | 存在，现 236 行 | §2 已由 eng-designer 写入（含本轮一块一模型变更）；§3 已由评审子代理写入；§5 归 eng-coder、§1/§4/§6 归主 agent | 现 236 → ≤ +120 |
| `src/data_exchange/models.py` | 存在，163 行 | 不改（`BindingSpec.design` 已是产物命名依据，无需新字段） | 163 → 163 |
| `src/data_exchange/aedt_parser.py` | 存在，316 行 | 不改（§3 解析器不动） | 316 → 316 |
| `src/simulink_controller/dialog.py` | 存在，423 行 | 不改（§4.2 Browse 与窗口操作已实测） | 423 → 423 |
| `src/simulink_controller/binder.py` | 存在，323 行 | 模型生命周期拆为「每块新建 / 保存 / 关闭」：`save_model` 改为带目标路径的 `save_system`，新增 `new_model` / `close_model`，`model_name` 改由 design 名推导 | 323 → ≤ +40 |
| `src/simulink_controller/verifier.py` | 存在，118 行 | 不改（§4.3 判据不变） | 118 → 118 |
| `scripts/bind_simulink.py` | 存在，283 行 | `--out` → `--out-dir`（缺省 `.thincoder/tmp/simulink-binding`）；主循环改为每块新建/保存/关闭一个模型；结果表增输出文件路径列 | 283 → ≤ +50 |
| `tests/test_aedt_parser.py` | 存在 | 不改（解析面不变）；新增命名规则单测（design 名 → 文件名 / 模型名）建议落同文件 | 不变 / ≤ +30 |
| `config/base.yaml` | 存在 | 增输出目录缺省项（若已有配置层装下标则不动 yaml） | ≤ +3 |
| `.gitignore` | 磁盘上不存在（实测 `Test-Path` 为假），本批新建 | 新建（§5.2 规则） | ~40 |
| `help/README.md` | 存在，实测 66 行 | 目录总览内补仓库 URL 与 `repos/` 行的忽略说明（§5.3），不追加登记段 | 66 → ≤ +8 |

以上单文件均低于项目跨文件上限，无需拆分。

## 9. 验收标准

与 §6.3 的表一字不差地一一对应，不重复列出（同一判据写两处即两版会漂）。补充三条约束：

1. 设计文档存在且 §1–§9 齐全。
2. 全文档单行不超过 300 字符。
3. `models/manual/RotorySimulink_thincoder.aedt` 上 F1 的解析读数与被引用的行号一致。

## 10. 未决项与现在不能定的原因

| 未决项 | 为什么现在不能定 |
|---|---|
| `UserData` 除末尾索引序列外的字段序语义 | 只有单一实样，反推不能当设计前提；判据只依赖「前缀 + 关键子串包含 + 末尾索引序列」，不依赖其余字段序 |
| 选中 `.aedt` 后引擎未就绪时自动拉起 AEDT 的耗时 | 实测只知「会自动拉起、需要等待」，未测耗时分布；本批验收按「提前打开 AEDT」执行，自动拉起只记已知行为、不设超时判据 |
| 端口表回退路径的多段取舍（§3.2 第 5 步） | 库定义段实测有三段（`:9954` 'SimulinkData'，`:10210` / `:10299` 'SimulinkData1'），实例 `SimulinkModelName='SimulinkData1'`（`:49478`）会命中后两段；现拟「取同名最后一段」 |
| 同上：何时能实测 | 唯一实测样本的实例帧自带端口行（`:49480-49529`），回退路径本批走不到；拿到一个精简存盘的 `.aedt` 才能回填取舍规则。主路径已覆盖本批实样 |
| 同 design 多元件的文件名去重（§4.5 `_2` / `_3`） | 实测样本一个 design 只有一个元件，去重路径无实样；当前规则按「第二个起加后缀」实现，拿到同 design 两元件的 `.aedt` 才能验证 |
| 同模型多次绑定的失败机理 | 只知现象（第 2 块 `set_param` 后对话框 60 s 不出现，稳定复现 3 次）与四个已被探针排除的假设；根因未定位。设计采一块一模型的隔离手段，不依赖对该机理的理解 |
