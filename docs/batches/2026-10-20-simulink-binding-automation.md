# 2026-10-20 · simulink-binding-automation
> 六段 append-only，一段一作者：§1 讨论（主 agent）· §2 批次任务与设计（eng-designer）· §3 设计评审（评审子代理）· §4 用户批准（主 agent）· §5 实施记录（eng-coder）· §6 验证与收口（父代理）。
> 编制：主 agent · 2026-10-20 · 来源 = 用户要求：Twin Builder ⇄ Simulink 联合仿真绑定自动化，给定 .aedt 自动批量生成已绑定的 AnsoftSFunction 块。
> 台账 = #1（simulink-binding · 归批）。前情 = 无（独立批）。
## §1 讨论（主 agent）
**状态行**：已收口 2026-10-20
<§1 模板占位：本批条目 / 关键判据 / 授权口径>

### 讨论与授权

#### 用户需求

给定一个 Twin Builder 工程文件（`.aedt`），自动在 Simulink 里生成对应的 `AnsoftSFunction` 块并完成信号绑定，
替代手工逐块点击 `Simplorer Link Assignment Dialog` 的重复劳动。

原始表述：「我手工搭建了一套 simplore+simlink 联合仿真模型，其中有一个问题很关键，就是 simplore link（Sim2SimDialog.exe），
但是我没有找到相关的调用接口，实现自动化绑定，首先查找有无相关案例或者代码，实在不行根据 pywinauto，完成自动化绑定开发」

#### 关键判据（用户历次裁决）

| 时间 | 裁决 | 依据 |
|---|---|---|
| 17:22 | 自动化程度选 B：连信号映射也自动填 | 给定映射表全自动绑定 |
| 17:24 | 确认 `ShowLinkDialog` 只负责弹窗、必须配界面自动化 | 官方函数无映射参数 |
| 17:31 | 索引不能写死，要按端口数动态生成 | 用户追问 |
| 17:37 | 新建两个不同端口数的 design（3 进 3 出、2 进 1 出）用于测试 | 验证通用性 |
| 19:28 | 改为「每个元件一个独立 `.slx`」 | 单模型双块必失败，长期排查无果，独立模型稳定 |

#### 实测事实（构成设计前提）

| 事实 | 证据 |
|---|---|
| `ShowLinkDialog(const char*)` 只有一个参数，不接收映射数据 | `AnsoftSFunction.h:17`；`libfunctions` 实测只返回该函数 |
| 改 `FunctionName` 为 `AnsoftSFunction` 会阻塞并弹模态框 | 实测卡 420 秒直至超时 |
| 端口名参数只读 | `set_param` 报「参数为只读」 |
| `UserData` 与 `Parameters` 可写 | 写入后读回成功 |
| 弹窗宿主是 `Sim2SimDialog.exe`，与 MATLAB 是兄弟进程 | `EnumWindows` + 父链实测 |
| 勾选后映射不会自动填满，索引全 `-1` | 点 OK 后读回 |
| `Autolink` 无效 | 用户实测「autolink没有用」 |
| 必须手动逐个 Link 才能建立映射 | 用户手工操作演示 + 前后 UserData 对比 |

#### 授权口径

设计与实现由本批交付；用户发起评审、批准设计、验收产物。
三套产物（`MatlabConnect.slx` / `Simplorer1.slx` / `Simplorer2.slx`）经用户打开确认为正常。

## §2 批次任务与设计（eng-designer）
**状态行**：设计完成
<§2 模板占位：本批条目（覆盖） / 设计档落点 / 机制设计 / 受影响文件与测试覆盖 / 验收对照 / 关键决策 / 上抛项>

### 本批条目（覆盖）

| # | 条目 | 覆盖需求 |
|---|---|---|
| 1 | `.aedt` 解析器：枚举 SimulinkData 元件、归属 design、取 TR 分析名 | F1 |
| 2 | 块生成 + 弹窗绑定执行器（MATLAB 引擎 + pywinauto 双线程） | F2 |
| 3 | 绑定结果核验（读回 Parameters / UserData 逐字段比对） | F3 |
| 4 | 错误处理与退出码 | F4 |
| 5 | 目录结构 + `.gitignore` 规则 + `help/repos/` 登记文件 | 用户要求（本批纳入） |

**本批不覆盖**：信号连线、已有 `.slx` 增删块、`.aedt` 改写、Maxwell / Motor-CAD 链路、图形界面。

### 设计档落点

`docs/design/simulink-binding.md`（本批新建）。

### 机制设计（要点，详见设计档）

- **三段流水线**：解析 → 绑定 → 核验，段间只传数据对象 `BindingSpec` / `BindingResult`。
- **双执行体握手**：`set_param(blk,'FunctionName','AnsoftSFunction')` 在 MATLAB 引擎子进程里阻塞，Python 主线程以 `background=True` 异步持有，pywinauto 在独立线程以 200 ms 轮询窗口判据（`#32770` + `Read link information from fileCheckBox` + 进程归属）接手，点 OK 后窗口销毁、引擎解阻。
- **三种异常**：窗口未出现 60 s 超时；单步操作超时；关窗 120 s 卡死则杀引擎重启。均写入 `BindingResult.status`。
- **design 归属走 Refdes**：`Compinst` 的 `ID` = 所在 `Instance` 段 `Refdes('<id>','<instance>')` 的第一个参数，取同段 `DesignEditor`（实测：ID 206 → `Refdes('206','MDL1')` → `MatlabConnect`）。
- **成功判据不解析 UserData 字段序**：只判前缀 `DataVer:2,` + 关键子串包含，避开单样本反推的未验证语义。

### 受影响文件与测试覆盖

| 文件 | 动作 | 预估行数 |
|---|---|---|
| `docs/design/simulink-binding.md` | 新建 | ~200 |
| `src/data_exchange/models.py` | 新建 | ~50 |
| `src/data_exchange/aedt_parser.py` | 新建 | ~180 |
| `src/simulink_controller/dialog.py` | 新建 | ~180 |
| `src/simulink_controller/binder.py` | 新建 | ~200 |
| `src/simulink_controller/verifier.py` | 新建 | ~90 |
| `scripts/bind_simulink.py` | 新建 | ~120 |
| `tests/test_aedt_parser.py` | 新建 | ~80 |
| `config/base.yaml` | 新建 | ~25 |
| `.gitignore` | 新建 | ~40 |
| `help/repos/` 内 README | 新建 | ~15 |

单测面只覆盖解析器（纯文本、可脱机）；绑定执行器靠实测 `.aedt` 走 F2 验收。

### 验收对照

| 需求 | 验收命令 | 判据 |
|---|---|---|
| F1 | `python scripts/bind_simulink.py --aedt models/manual/RotorySimulink_thincoder.aedt --dry-run` | 1 元件 `SimulinkData10`/`MDL1`，10 端口，`uA,uB,uC,TL` 方向 1，`iA,iB,iC,wm,THM,Te` 方向 0 |
| F2 | 同上去掉 `--dry-run`，`--out models/manual/_gen.slx` | 每块 `Parameters='-1'`，`UserData` 以 `DataVer:2,` 开头且含 `.aedt` 路径、`MatlabConnect`、`MDL1` |
| F3 | 同 F2，看读回比对表 | 每块字段比对表齐全，全一致退出码 0 |
| F4 | `--aedt models/manual/_not_exist.aedt` | 报错含「解析\|路径不存在」，退出码 2 |

### 关键决策

1. **双线程而非双进程**：MATLAB 引擎本身是子进程，pywinauto 在同进程另一线程即可；再拆一层进程只会增加 IPC 与同步面。
2. **直调 `set_param` 而非官方 `AnsoftLinkDialog.m` 包装**：包装内部已阻塞且只回写 `Parameters`，直调可拿到块句柄做精确核验；若核验读数恒为默认值，退回 `gcb` + 官方包装（设计档 §4.2 已写退路）。
3. **不解析 `UserData` 字段序**：字段语义来自单一实样反推，未验证；判据改用前缀 + 子串包含，避免把未验证假设写死。
4. **`models/` 只提交源文件**：运行产物每个求解周期都变、二进制无法 diff，提交只会让仓库随时间膨胀。

### 上抛项

无待裁项。三处未实测环节（Browse 原生对话框控件形态、`UserData` 字段序、直调 vs 官方包装）已在设计档 §10 说明为何现在不能定，并各给主方案 + 备选路径。

### 本批覆盖的需求条目

| 需求 | 本批做什么 | 设计坐标 |
|---|---|---|
| F1 从 `.aedt` 发现绑定源 | `.aedt` 文本解析出 `BindingSpec`（design / instance / 端口表），`--dry-run` 只出解析结果 | 设计 §3；验收命令设计 §6.3 |
| F2 批量生成已绑定的 S-Function 块 | 双线程（MATLAB 引擎 + pywinauto）逐块走对话框，每块绑定核验后立即 `save_system` | 设计 §2.2、§4.1、§4.5；验收命令设计 §6.3 |
| F3 绑定结果核验 | 读回 `Parameters` / `UserData`，按「前缀 + 三个关键子串」判成功，打印字段比对表 | 设计 §4.3；验收命令设计 §6.3 |
| F4 失败可见 | 四段式错误信息（阶段 / 对象 / 判据 / 实测值）+ 退出码 0–3，失败不静默 | 设计 §6.1、§6.2；验收命令设计 §6.3 |

### 本批明确不做的条目

- 不做信号连线、不改已有 `.slx`、不改写 `.aedt`（需求 §4 边界，设计 §7）。
- 不碰 Maxwell / Motor-CAD 链路（`src/motorcad_controller/` 本批不建）。

### 受影响文件清单

见设计 §8 表格（11 个新建文件 + `help/README.md` 追加登记段）。所有单文件低于项目跨文件上限，无需拆分。

### 验收标准

与设计 §6.3 的 F1–F4 验收命令表一一对应，不另列一份（同一判据写两处即两版会漂）。设计侧补充约束：设计文档 §1–§10 齐全、单行不超过 300 字符、F1 的解析读数与被引用行号一致。

### 评审修复轮（#1–#7 · 2026-10-20）

按用户裁决修复评审 #1–#7；#8 / #9 暂缓、#10 非问题，均未改动。

| # | 改了什么 | 落点 |
|---|---|---|
| 1 | §8 现存文件标「实测当前行数 → 改后上限」：设计档 336 → ≤+15、批次记录 125 → ≤+120、`help/README.md` 66 → ≤+8；`.gitignore` 保持「不存在」并写明「磁盘上实测不存在，本批新建」 | 设计 §8 |
| 2 | §1 补 `help/repos/` 三仓库目录/入口形态的勘察与不采用理由（发布单元不同：库/server vs 本机命令行+控制器包） | 设计 §1 |
| 3 | §1 新增「勘察到但按边界不用」段：官方流程图含 Link/Autolink，按需求 §4 边界主动跳过，理由是勾选 Read link information 后映射已自动填满；§7 边界加一行指回该段 | 设计 §1、§7 |
| 4 | §3.2 第 3 步判据由「同帧」改为「`Compinst` 帧及其全部嵌套子帧（子树）」，并写明实现形式（进帧置标志到配对 `$end` 之前）与实测依据（`:49461` → `:49472` → `:49473`，字段在第 2 层） | 设计 §3.2 |
| 5 | §3.2 第 5 步补多段命中取舍（取同名最后一个匹配段），并注明回退路径本批无实样、登记进 §10 未决项（两条：取舍规则 / 何时能实测） | 设计 §3.2、§10 |
| 6 | §6.3 增「F3（不一致）」行：期望值人为改错，比对表四列齐全，退出码 1；增「F4（绑定后参数不符）」行：该块判失败走四段式，不计通过，退出码 1 | 设计 §6.3 |
| 7 | §8 批次记录行改为与磁盘一致：§2 已由 eng-designer 写入，后续追加 §3（评审，已写）与 §5（实施），§1/§4/§6 归主 agent | 设计 §8 |

**doc_check**：`gate` 模式对 `docs/design/simulink-binding.md` 判定 PASS（0 命中）。设计档 319 → 336 行。

**上抛项**：无。回退路径取舍规则未实测的缺口已按 #5 允许的第二种处置登记进 §10，不在本轮强定。

### 修正轮：按实测回填设计档与需求档（2026-10-20）

**本批覆盖的需求条目**：F1 / F2 / F3 / F4 全部（修正不新增需求，只把已有四条从「推断判据」改为「实测判据」）。

**本批明确不含**：F1 解析器的端口表回退路径（§3.2 第 5 步）仍无实样，沿用「取同名最后一段」；自动拉起 AEDT 的耗时分布只记为已知行为，不设超时判据。

**改动文件**：

| 文件 | 章节 | 动作 |
|---|---|---|
| `docs/design/simulink-binding.md` | §1 | 「勾选后映射自动填满」理由作废，改为「直接构造写回 UserData」 |
| 同上 | §2.2 判据③ | MATLAB 进程组 → `Sim2SimDialog.exe` 宿主 + 祖先链含本会话 `MATLAB.exe`；判据② 补标题 |
| 同上 | §2.2 步 4 | 去掉「轮询 Parameters 直到与期望一致」（Parameters 不作判据） |
| 同上 | §4.1 | 8 步扩为 14 步：勾选→Browse→填路径→选 design→combo1 自动→OK→读回→构造写回→核验→保存；补三条控件定位事实 |
| 同上 | §4.2 | 「未实测 + 两级备选」→「已实测 + 精确控件定位 + 一条兜底 + 前置条件」 |
| 同上 | §4.3 | 判据去掉 `Parameters=='-1'`；新增索引构造规则 `range(out_n)+range(in_n)` 与写回/持久化实测 |
| 同上 | §4.4 ② | 状态污染断言改为「显式 select design + 读回 window_text 比对」 |
| 同上 | §6.3 F2 行 | `Parameters='-1'` → §4.3 三条判据 |
| 同上 | §7 | 补「改由脚本构造写回 UserData，绕开逐项 UI 点击」 |
| 同上 | §8 / §10 | 行数读数更新；旧未决项「Browse 控件形态」删除，新增「自动拉起 AEDT 耗时」 |
| `docs/requirements/simulink-binding.md` | §3 F2/F3 验收、§4 边界、§6 约束表 | 判据改以 UserData 为准；「勾选后自动填满」理由删除并改正；约束表补 design 框与宿主进程两条实测 |

**受影响文件（本轮实际只动两份文档，不涉代码）**：`docs/design/simulink-binding.md`（337 → 395 行）、`docs/requirements/simulink-binding.md`（93 → 98 行）。

**验收标准**：见上文逐条覆盖——① 设计档四处全部改完；② 窗口判据③ 改看 `Sim2SimDialog.exe` 祖先链；③ §4.1 序列含全流程 14 步；④ §4.2 已实测并写明兜底；
⑤⑥ 判据以 UserData 为准并说明索引规则；⑦ 需求档错误理由已改正；⑧⑨ design 显式选择与文件选择后的下拉框刷新已写入；⑩ `doc_check` gate PASS；⑪ 无超 300 字符行；⑫ §5 / §9 未改动。

**可执行验证（判据形式）**：`doc_check(mode="gate", docs=[两份])` → `DOC-CHECK GATE: PASS`；设计档 395 行 / 需求档 98 行，超 300 字符行 0 条（读数见本轮交付报告）。

### 变更轮：产物形态改为「每个元件一个独立 .slx」（2026-10-20）

**本批覆盖的需求条目**：F2（生成形态 + 验收）、§7 使用形态（`--out` → `--out-dir`）、§4 边界补一条「不覆盖同名文件」。F1 / F3 / F4 不变（F4 的退出码表只补一句产物落盘）。

**本批明确不含**：解析器（§3）、Browse 操作（§4.2）、核验判据与索引规则（§4.3）一律不动；同模型多次绑定的根因不追（设计 §10 已登记为未决项）。

**变更依据（实测）**：
- 单模型装三块（正式实现）：第 1 块 ok → 第 2 块 `set_param` 后对话框 60 s 不出现 → 第 3 块 ok，稳定复现 3 次。
- 探针每块独立模型（`_probe_multi2.py`）：`MatlabConnect` Ports=(4,6) / `Simplorer1` Ports=(3,3) / `Simplorer2` Ports=(2,1)，三套全部 ok。
- 同引擎连跑两次（`_probe_seq.py`）：两次都 ok ⇒ 引擎复用无问题；失败信息里的「命中 #32770 窗口 3 个」是系统常驻窗口（IDMan ×2、ansysedt）噪音，不是残留。
- 用户裁决：采用 B（每元件一个独立 `.slx`）。

**设计落点（`docs/design/simulink-binding.md` 416 行）**：

| 章节 | 改前 | 改后 |
|---|---|---|
| §1 一句话方案 | 「逐块走…」在一个模型里 | 每元件各建独立 `.slx`；新增「为什么一个元件一个模型」实测段 |
| §2.1 流水线 | 段间只传数据对象 | 增「模型粒度」段：一 `BindingSpec` 一模型、生命周期五步、`--out-dir` 语义 |
| §2.3 异常表 | 卡死杀引擎 | 补「该块的模型文件此时未必存在，见 §4.5」 |
| §4.1 动作序列 | 14 步，模型由外部建 | 0 步 `new_system(<design名>)`、1 步块路径带模型名、14 步 `save_system` 到 `<输出目录>/<design名>.slx`、15 步 `close_system` |
| §4.3 持久化句 | 「save_system 再 close_system + load_system」 | 改为不丢绑定状态说明，并指向 §4.1 步 15 |
| §4.4 | 「多块批量的状态污染」靠断言 ComboBox 状态 | 「多块批量的隔离手段：一块一模型」——隔离靠模型边界，不靠控件断言；剩两条干扰（design 显式选、引擎重启）保留 |
| §4.5 | 「每块完成即保存」单输出文件 | 「每块的保存、关闭与命名」：命名 `{design名}.slx`、`--out-dir` 缺省、非法字符转义、撞名 `_2/_3`、旧文件不覆盖 |
| §5.1 目录 | 无产物流 | 增 `.thincoder/tmp/simulink-binding/` 缺省输出目录 |
| §6.2 退出码 | 0/1/2/3 四行 | 0 补「每块各自 .slx 已落盘」、1 补「含输出文件路径」、3 补「输出目录无法创建」 |
| §6.3 验收 | F2 用 `--out models/manual/_gen.slx`；F4 用 `--out x.slx` | F2/F4 改 `--out-dir`；F2 判据改「3 个文件各含 1 块」；补两条模型粒度读数 |
| §8 受影响文件 | 11 个文件都标「不存在 / 新建」 | 改为实测现状（`src/` 五文件已存在：316/163/423/323/118 行；`scripts/bind_simulink.py` 283 行）与本轮动作 |
| §10 未决项 | 有重复标题（两个 §10） | 重复段删除；新增两条未决（同 design 多元件去重无实样、同模型多次绑定根因未定位） |

**代码侧影响（给 eng-coder 的执行面）**：`binder.py` 新增 `new_model` / `close_model`，`save_model` 改为带目标路径；`scripts/bind_simulink.py` 主循环由「一个模型跑完所有块」改为「每块新建 / 保存 / 关闭」。

**验收对照**：`doc_check(mode="gate", docs=[设计档, 需求档])` → PASS（0 命中）；两档超 300 字符行 0 条（实测：设计档 416 行、需求档 106 行）。

**上抛项**：无待裁项。

## §3 设计评审（评审子代理）

### 轮次 1（评审子代理）

### 设计评审轮次 1 — docs/design/simulink-binding.md

评审对象：`docs/design/simulink-binding.md` 全文（Twin Builder ⇄ Simulink 绑定自动化设计）；对照需求 `docs/requirements/simulink-binding.md`。

| # | 类别 | 级别 | 问题 | 建议 |
|---|------|------|------|------|
| 1 | 受影响文件行数标注 | 🟡 | 设计 §8 受影响文件清单（`docs/design/simulink-binding.md:287-302`）**全部为新建文件**，仅给 `~N` 预估行数，未标注**现存文件**的当前行数与预期增量（`≤±N` 或"结构不变"）。清单里确有 3 个现存文件：`docs/batches/2026-10-20-simulink-binding-automation.md`（`:290`）、`help/README.md`（`:300`）、`.gitignore` 在 `:299` 被写成「不存在」——但被忽略的 `help/` 目录下确有 `help/README.md`（实测 `help/README.md:1-30` 存在，且设计 §5.3 自己在 `:245` 引用「`help/README.md:12-18` 的现有形态」，与 §8 的「不存在」自相矛盾）。另外 `~200` 行等预估值对新建文件尚可，但对 `help/README.md` 的「~8」增量缺 `≤±N` 形式的显式上限标注。 | 在 §8 表格补出每个**现存**文件的当前行数并给出 `≤+N`/`≤±N` 形式的上限；修正 `.gitignore` 一行的「不存在」表述（该文件是否真不存在应以磁盘为准，但需与 `help/README.md` 一行的「存在」口径统一）；`help/README.md` 的增量标注为 `≤+N`。跨文件上限判断（§8 `:302`「以上单文件均低于项目跨文件上限，无需拆分」）已有，保留。 |
| 2 | 最近先例 | 🟡 | 设计 §1（`docs/design/simulink-binding.md:17-18`）给了最近先例行：「项目内无同类先例（`docs/design/` 本批新建，此前无设计文档）」+ 对齐依据取 `AGENTS.md` 目录约定。**实测该声明成立**（`docs/` 下仅 3 个 md：本设计、需求、批次记录；`glob docs/**/*.md` 结果）。但「无先例」的声明之外还缺一项：**跨文件/跨工具的同类自动化脚本先例**（`scripts/` 目录规划在 `AGENTS.md` 但尚未落地）未在文中说明「为何不参考 `help/repos/pyaedt-mcp/` 的 server 入口形态」或类似。 | 该行本身合规（有声明、有对齐依据）。建议补充一句为何未采用任何 `help/repos/` 下已有工程的目录/入口形态作参照，使「无先例」的勘察面与 §1 `:20-21` 的公开资料勘察面一致。 |
| 3 | 公开资料勘察 | 🟡 | 设计 §1（`docs/design/simulink-binding.md:20-21`）给了勘察行，声明查过 `help/ansys-help-topics/`（含「Simplorer Link Assignment Dialog」章节）、`help/repos/pyaedt-mcp/`（无相关内容）、`help/repos/matlab-agentic-toolkit/`（无相关内容）。**实测三项均成立**：章节存在于 `help/ansys-help-topics/Twin Builder/Twin Builder.md:23103`；`Read link information from file` 见同文件 `:23107`。**但勘察结论与设计机制存在一处未被消化的官方文档差异**：官方帮助 `:23149-23153` 的流程是「勾选 Read link information from file → Browse 选 .aedt → **用 Link/Autolink 按钮建立想要的信号连线** → OK」，而需求 §4（`docs/requirements/simulink-binding.md:49`）与设计 §7（`:283`）均声明「不驱动点击 Link/Autolink」。二者可并存（本批只放置块、不连线），但设计未在勘察行或 §7 里点明「官方流程含 Link/Autolink 步骤、本批按需求边界跳过」这一对照，读者无法判断该偏差是需求裁定还是遗漏。 | 在 §1 勘察行或 §7 边界里补一句对照：官方帮助要求的 Link/Autolink 步骤按需求 §4 明确不做，只勾选 Read link information 让映射自动填满（需求 §6 `:71` 有实测支撑）。这样「勘察到但未采用」与「没勘察」在文档上可区分。 |
| 4 | 清晰度 | 🟡 | 设计 §3.2 第 3 步（`docs/design/simulink-binding.md:92`）「同帧内出现 `ComponentDataType='SimulinkData'` ⇒ 判为 SimulinkData 元件」用词「同帧」有歧义：实测该字段在实例里位于 `Compinst` 帧**嵌套的** `CompData` 子帧内（`models/manual/RotorySimulink_thincoder.aedt:49472-49473`：`$begin 'CompData'` 在 `49472`，`ComponentDataType='SimulinkData'` 在 `49473`），并非 `Compinst` 帧的直接行。若实现按「当前栈顶帧」严格判等会**零命中**。§3.2 第 2 步（`:91`）说「进入 `Compinst` 帧时记录」、第 4 步（`:93`）说「在该实例所属的 `Instance` 段内按 `ID` 查」，实现者需要自行推断「同帧」=「`Compinst` 帧的子树」。 | 把 §3.2 第 3 步改成明确的子树判据（例如「在 `Compinst` 帧及其嵌套子帧内出现 `ComponentDataType='SimulinkData'`」），避免「同帧」被实现为帧名严格相等而零命中。同理 §3.2 第 2 步记录的是 `Compinst` 帧起止。 |
| 5 | 清晰度 | 🟡 | 设计 §3.2 第 5 步（`docs/design/simulink-binding.md:94`）端口表回退条件是「若实例帧内无端口行（实例精简存放），回退到 `$begin 'SimulinkData…'` 库定义段按 `SimulinkModelName` 匹配」。实测本样例**实例帧内已有完整端口行**（`RotorySimulink_thincoder.aedt:49480-49529`，`SimulinkName0..9` + `SimulinkDirection0..9`），故主路径可用、回退路径本批无法验证；回退路径依赖 `SimulinkModelName` 匹配库定义段，而实例的 `SimulinkModelName='SimulinkData1'`（`:49478`）在库定义段里对应的是 `:10210`/`:10299` 那两段（`SimulinkModelName='SimulinkData1'`），`$begin 'SimulinkData'` 段（`:9919`）的 `SimulinkModelName` 是 `'SimulinkData'`（`:9954`）——说明**库定义段有三段、名字不一**，回退匹配可能命中多段。设计未说明多段命中时如何取舍。 | §3.2 第 5 步补一句回退路径的多段命中处理（取首个 / 判歧义并报 F1 失败），或在 §10 未决项里登记「回退路径本批无实样、未经实测」。 |
| 6 | 验收标准 | 🟡 | 设计 §6.3（`docs/design/simulink-binding.md:274-277`）的 F1–F4 验收命令与判据**可验证、具体**（含退出码、端口名与方向逐一列出），但 F3 的验收（`:276`）判据「打印每块字段比对表，全一致时退出码 0」缺少**不一致时**的可验证判据——需求 F3（`docs/requirements/simulink-binding.md:36`）明确要求「不一致时明确列出哪个字段、期望值、实际值」。设计中该判据只在 §6.3 F3 行以「字段 / 期望 / 实际 / 结论」列出列头，未给出不一致场景的验收命令与期望退出码（F4 `:277` 只覆盖解析失败，未覆盖「绑定后参数不符」这一需求 F4 `:40` 明确列举的失败面）。 | §6.3 补一行或补 F3 判据：绑定后参数不符时的期望退出码（应为 1，按 §6.2 `:266`）与比对表须含期望/实际两列的断言；或在 F4 行补一个覆盖「参数不符」的验收命令。 |
| 7 | 方法论合规 / 文档归属 | 🟡 | 项目无 `PROJECT-MANIFEST.json`、无 document map、未声明项目标准文档（评审上下文明确说明 Document ownership 判据降级）。设计文档**确实存在**（`docs/design/simulink-binding.md`，非 🔴），且按 `AGENTS.md` 的规划目录放位正确。但设计 §8（`:290`）声明追加批次记录 §2，而实测批次记录 §2 **已有内容**（`docs/batches/2026-10-20-simulink-binding-automation.md:8-94`，状态行「设计完成 2026-10-20」），说明 §2 已由设计侧写过；§8 的「本次动作」与现状不符（写的是未来时「追加 §2」，实际已完成）。 | 把 §8 中批次记录一行的「本次动作」改为与现状一致（§2 已写完 / 或本批不再写 §2），避免受影响文件清单与磁盘状态不符。 |
| 8 | 范围 | 🔵 | 设计 §5.2（`docs/design/simulink-binding.md:209-232`）的 `.gitignore` 规则清单与 §5.3（`:234-251`）的 `help/README.md` 登记方式，规模明显大于需求 F1–F4 的功能面（需求全文 `:1-92` 未提 git 策略或资料库登记）。设计 §6.3 之外未声明这是「本批一并纳入」的独立条目——批次记录 §2 确实把它列为第 5 条（`docs/batches/2026-10-20-simulink-binding-automation.md:20`「目录结构 + `.gitignore` 规则 + `help/repos/` 登记文件 | 用户要求（本批纳入）」），故有授权来源，不构成范围蔓延，但设计文档自身未给出该授权指向。 | 在 §5 开头补一句本节的授权来源（批次记录 §2 第 5 条 / 用户要求），使设计文档单独阅读时也能看出这不是自发的范围扩张。 |
| 9 | 可行性 | 🔵 | 设计 §4.2（`docs/design/simulink-binding.md:144-156`）把 Browse 原生对话框列为「本方案唯一未实测环节」，给主方案 + 两级备选 + 降级路径，处理得当。但备选一与备选二（`:149-150`）在机制上高度重叠（都是往文件名栏输入文本后回车，区别仅在 `SendKeys` / `type_keys`），实际只提供一条独立的技术路线；真正的第二路线（例如直接对 `#32770` 发 `WM_SETTEXT` 给文件名 Edit 句柄、或用 `GetOpenFileName` 之外的方式）未列出。这是设计自陈降级路径的完整性，不影响主方案可行。 | 若不打算扩充备选，把「两级备选」改为「一个备选 + 一个输入方式回退」，并在 §10 未决项里保留 Browse 控件形态待实测即可；若保留两级，可补一条与 `type_keys` 机制上真正不同的路线。 |
| 10 | 可行性（已完成核验项） | 🔵 | 设计的多项关键实测断言**经独立核验成立**，记录备查：① `ShowLinkDialog` 只有一个 `const char*` 参数——`E:\ANSYS Inc\v261\AnsysEM\cpl\matlab\r2024b\AnsoftSFunction.h:17` 精确匹配；② 官方包装在 `ret==true` 时执行 `set_param(gcb,'Parameters','-1')`——`AnsoftLinkDialog.m:11-13` 精确匹配；③ `.aedt` 结构坐标全部正确：库定义 `$begin 'SimulinkData'` 在 `:9919`、`ComponentDataType` 在 `:9949`、`SimulinkName0..9` 在 `:9956-10003`、`Compinst` ID 206 在 `:49462`、`CompName='SimulinkData10'` 在 `:49464`、`InstanceName` MDL1 在 `:49469`、`Instance` 段 `DesignEditor='MatlabConnect'` 在 `:57664`、`ID='181'` 在 `:57665`、`Refdes('206','MDL1')` 在 `:57679`、`DesignName` 四处 `:68560/68682/69349/69646`、`'Nominal Setups'[1: 'TR']` 在 `:69353`；④ 端口方向与需求 F1 验收一致（`uA/uB/uC/TL` = 1，`iA/iB/iC/wm/THM/Te` = 0，`:49480-49528`）。设计 §9 第 3 条「F1 的解析读数与被引用的行号一致」经核验成立。 | 无需改动。此项为证据确认，不构成缺陷。 |

**注**：需求文档 `docs/requirements/simulink-binding.md` §8（`:90-92`）声明「待定项：无。所有影响实现的判断已由实测确定」，但设计 §10（`:313-318`）列了三处未实测项（Browse 控件形态、UserData 字段序、直调 vs 官方包装）。二者不矛盾——需求说的是「影响实现可行性的判断已定」，设计说的是「具体参数/控件形态待实测」——但两处可让读者误以为存在未决冲突。列为 🔵 观察，不另立行。

**计数**：🔴 0 · 🟡 7 · 🔵 3

VERDICT: pass

## §4 用户批准（主 agent）

### 用户批准

| 项 | 内容 |
|---|---|
| 批准时间 | 2026-10-20 16:14 |
| 批准对象 | `docs/design/simulink-binding.md`（337 行，doc_check PASS） |
| 评审结论 | advisor 评审 VERDICT pass，🔴 0 · 🟡 7 · 🔵 3 |
| 意见处置 | 7 条已修并核验；#8、#9 用户裁决暂缓；#10 为核实性结论非缺陷 |
| 批准方式 | 用户回复「批准」 |

### 批准范围

实现按设计文档 §4 执行，边界以设计 §7 为准：

- 输入 `.aedt` 路径，输出新建空白 `.slx`
- 自动发现所有 `SimulinkData` 元件，批量生成已绑定的 `AnsoftSFunction` 块
- **不做**：信号连线、改已有 `.slx`、点 Link/Autolink/NEW/DELETE、改 `.aedt` 内容、Maxwell / Motor-CAD 链路、图形界面
- 顺带落地 `.gitignore`（按设计 §5.2 规则）与 git 基线提交

### 已知的未实测环节（实现时必须真跑验证）

1. **§4.2 Browse 原生文件对话框**——主方案 `set_edit_text` + 两级备选（`SendKeys` / `type_keys`）。三条全不通时按设计 §4.2 退路降级为「打印待绑定清单、人工完成」，**必须明确标为降级，不得标为通过**。
2. **§3.2 第 5 步回退路径的多段取舍规则**——「取同名最后一个匹配段」为推断规则。实测样本主路径可用（实例帧内端口行完整，`.aedt:49480-49529`），回退路径本批无实样，已登记 §10 未决项。

### 授权口径

用户批准于批次记录 §4 成文；实现阶段由 eng-coder 执行，落地记录写入 §5，验收与收口由主 agent 写入 §6。

## §5 实施记录（eng-coder）
## §6 验证与收口（父代理）

### 验证与收口

**状态行**：验证完成 2026-10-20

#### 验收读数

| 需求 | 项 | 命令 | 读数 | 结论 |
|---|---|---|---|---|
| F1 | `.aedt` 解析 | `bind_simulink.py --aedt <样本> --dry-run` | 3 个元件：`SimulinkData10`/`SimulinkData2`/`Simulink_Control`；design 为 `MatlabConnect`/`Simplorer1`/`Simplorer2`；端口 6/4、3/3、1/2；索引 `[0,1,2,3,4,5,0,1,2,3]`/`[0,1,2,0,1,2]`/`[0,0,1]`；退出码 0 | 通过 |
| F2 | 批量绑定 | `bind_simulink.py --aedt <样本> --out-dir .thincoder/tmp/final3` | 通过 3 / 失败 0；产物 `MatlabConnect.slx` 71399B、`Simplorer1.slx` 71192B、`Simplorer2.slx` 71364B；退出码 0 | 通过 |
| F3 | 核验表 | 同 F2 | 每块打印前缀/路径/design/instance/末尾索引/全文六行比对，结论均为「一致」 | 通过 |
| F4 | 错误处理 | `bind_simulink.py --aedt <不存在路径> --out-dir <目录>` | 报错「解析 \| 路径存在且可读 \| 路径不存在」，退出码 2 | 通过 |
| 单测 | `pytest tests/ -q` | 11 passed | 通过 |
| 代码质量 | `ruff check src/ scripts/ tests/` | All checks passed | 通过 |

#### 产物二次验证

三个 `.slx` 重新 `load_system` 后读回：

| 文件 | 块 | Ports | design | 索引 |
|---|---|---|---|---|
| `MatlabConnect.slx` | `MatlabConnect/MDL1` | 4 进 6 出 | MatlabConnect | `0,1,2,3,4,5,0,1,2,3` |
| `Simplorer1.slx` | `Simplorer1/MDL1_2` | 3 进 3 出 | Simplorer1 | `0,1,2,0,1,2` |
| `Simplorer2.slx` | `Simplorer2/MDL1_3` | 2 进 1 出 | Simplorer2 | `0,0,1` |

用户已打开确认三个文件正常。

#### 实施中修正的缺陷

7 项，逐条列在 §5 应由 eng-coder 落笔（见下「未落笔项」）。其中三项是实质缺陷，不修则交付物不可用：
`save_system` 未传路径（报成功却零产物）、无落盘校验（前者的潜伏条件）、名字段顺序反了（与手工真值不符）。

#### 形态变更

「一个 `.slx` 装全部块」实测第 2 块必失败（稳定复现 3 次），用户裁决改为「每元件一个独立 `.slx`」。
设计 §4.4、需求 F2 已同步；改后三块全过。变更依据与排除过程记录在 §5 位置（待 eng-coder 补记）。

#### 未落笔项

**§5 实施记录未写入**：一段一作者，§5 归 eng-coder。本批两名 eng-coder（#6 超轮上限、#8 遇 API 限流）均未完成交付报告，
主 agent 直接修正了余下缺陷。§5 内容已在 §6 中以「实施中修正的缺陷」与「形态变更」两节留档，不阻断本批收口；
若后续需要 §5 完整记录，须另起一批由 eng-coder 补写。

#### 遗留技术项

1. **同模型多次绑定失败的根因未定位**（已绕开，未解决）：本批采用「一元件一模型」回避，机理未查明。
   影响面：若将来需要在一个模型内放多个块，需重新调查。
2. **`RotorySimulink_thincoder.aedt:50951` 附近可能残留测试写入的链接索引**：用户手工 Link 时在 `.aedt` 内留下了绑定痕迹。
   本工具的解析只读不写，不受影响；但该文件已非原始状态。

#### 文档检查门

`doc_check(mode="gate")` 对 `docs/design/simulink-binding.md`（416 行）与 `docs/requirements/simulink-binding.md`（106 行）：PASS，0 命中。

#### 用户文档面同步

无用户可见能力变更（本批为新增工具，未改动既有界面或交付物）。

#### 暂缓批复核

无暂缓批。

#### 收口结论

本批交付完成：`.aedt` → 批量生成已绑定 `AnsoftSFunction` 块（每元件一个 `.slx`）。
F1–F4 全部通过，单测 11 个通过，lint 通过，产物经用户确认可用。
