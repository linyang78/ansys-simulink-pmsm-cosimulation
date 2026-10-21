# Ansys-Simulink PMSM Cosimulation Scripts

[English](README.md) | **中文**

PMSM（永磁同步电机）多域联合仿真自动化工具集。

把 **Motor-CAD**（快速建模）、**Ansys Maxwell**（有限元求解）、**Twin Builder**（驱动电路）、**MATLAB Simulink**（闭环控制）
串成一条自动化链路，用于电机的建模仿真、控制策略验证与故障注入分析。

以宝马 i3（e11）IPM 电机为贯穿案例。

---

## 这个仓库解决什么问题

做电机仿真时，真正费时的不是跑一次 FEA，而是**工具之间的搬运**：

| 痛点 | 典型耗时 | 本仓库的做法 |
|---|---|---|
| 从 Motor-CAD 导出 ECE 等效电路，手工点十几步，参数容易填错 | 每次 20–30 min | `dist/ece-export` 一条命令 |
| Twin Builder 的电机模型要逐个绑定到 Simulink，靠鼠标点对话框 | 每个模型 5–10 min | `dist/simulink-binding` 批量绑定 |
| Maxwell 的 ECE 提取要在电路编辑器里拖元件、配参数扫描 | 每次 30 min+ | `dist/maxwell-ece` 五步流程 |

三个工具都做成**命令行 + 明确退出码**，不依赖 GUI 点击，可以直接嵌入脚本或由 agent 调用。

---

## 三个工具

### 1. `dist/simulink-binding` — Twin Builder ⇄ Simulink 绑定

从 `.aedt` 里找出 `SimulinkData` 元件，为每个元件生成独立的 `.slx`，
里面含一个 `AnsoftSFunction` 块并完成绑定参数写入。

```powershell
# 先探路，看有多少个可选元件
python scripts/bind_simulink.py <工程.aedt> --dry-run

# 正式生成
python scripts/bind_simulink.py <工程.aedt> --out-dir <输出目录>
```

**产物**：`<输出目录>/<design名>.slx`，一个模型一个块。

**为什么一块一个模型**：实测同一模型里连续绑多个块时，第 2 块必然失败（绑定对话框 60 s 不出现），
改成每块独立模型后全部成功。根因未定位，按实测可用形态定型。

**退出码**

| 码 | 含义 | 该怎么做 |
|---|---|---|
| 0 | 全部成功 | 读 `<out-dir>/*.slx` |
| 1 | 部分失败 | 看 stdout 结果表的 `FAIL` 行 |
| 2 | 解析失败（路径/无元件） | **不要重试**，输入问题 |
| 3 | 引擎失败（MATLAB 起不来） | 检查环境后**可重试一次** |

---

### 2. `dist/ece-export` — Motor-CAD ECE 等效电路提取

从 Motor-CAD 的 `.mot` 模型导出 Twin Builder 可直接导入的 **ECE 三件套**（SML / TXT / MAT），
并可从 MAT 反推电机参数、计算 PI 控制参数。

```powershell
# 先校验配置
python scripts/run_ece_export.py --config config/ece_config.json --dry-run

# 正式导出
python scripts/run_ece_export.py --config config/ece_config.json

# 从结果算控制参数
python scripts/calc_control_params.py --mat <ECE_map.mat> --json-out params.json
```

**产物**

```
<output_dir>/
├── ECE_<base>_map.mat       饱和图原始数据
├── ECE_<base>_txt_file.txt  可读查表（Ψd/Ψq/Ψ0/转矩）
└── ECE_<base>_sml_file.sml  ← 导入 Twin Builder 用这个
```

**⚠️ 网格必须包含 0 A**：Motor-CAD 硬性要求 `Id = 0` 的点存在。
所以 `2 × id_max / current_step` 必须是偶数（点数 = 段数 + 1 = 奇数），否则会白跑几小时才报错。
脚本会在跑 FEA 前本地校验。

| 段数 | 点数/轴 | 步长（±433 A） | 负载点 | 实测耗时 |
|---|---|---|---|---|
| 8 | 9 | 108.25 A | 81 | 5.2 min |
| 20 | 21 | 43.30 A | 441 | 29.5 min |
| 60 | 61 | 14.43 A | 3,721 | 243.5 min |

**退出码**：0 成功 · 1 导出失败（可重试）· 2 配置不可用（不要重试）· 3 Motor-CAD 连不上

---

### 3. `dist/maxwell-ece` — Maxwell 原生 ECE 提取

在 Maxwell 2D 里用 **ECE3_Model + ECER_Model** 组合提取电机的饱和与转矩查表，
产出 `.sph` 网表 + `.sml` 模型 + `.txt` 查表。

与工具 2 的区别：工具 2 走 Motor-CAD 的解析模型（快），工具 3 走 Maxwell 的有限元解（准，但慢）。
故障样机、几何改型后的模型只能用这条路径。

```powershell
$py  = 'python'
$cli = 'scripts/maxwell_ece.py'
$mot = 'models/e11_PMSM_IPM.aedt'

& $py $cli inspect  $mot --write config/inspection.json      # 离线读工程结构
& $py $cli draft    $mot --design PMSM_Healthy --setup Setup1 --write config/draft.json
& $py $cli validate config/draft.json --inspection config/inspection.json
& $py $cli prepare  config/draft.json                        # 隔离副本
& $py $cli run      config/draft.json                        # 启动 AEDT 求解
```

**五步流程**：前三步离线（不启动 AEDT），`prepare` 复制到隔离目录，`run` 才真正求解。

**`inspect` 自动识别**：design 名、setup、绕组组、运动设置全部从 `.aedt` 文本解析，
不依赖写死的名字。多个 design/setup 时必须显式指定 `--design` 和 `--setup`，
工具不会替你挑（防止选错）。

**产物**：`<output_dir>/<run-id>/ece_model.sml`（导入 Twin Builder 用）+ `ece_table.txt` + `.sph`

**核心 API 链路**（pyaedt 1.4.0 未直接暴露，走原生接口）：

```python
write_ece_netlist(...)                              # 按厂家模板生成 .sph
m2d.edit_external_circuit(netlist_file_path=sph)    # 挂载到 Maxwell
m2d.oanalysis.ExportECEData(export_args)            # 原生 ECE 导出
```

`ExportECEData` 成功时返回 `None`——不能用返回值判断成败，要看文件是否真的落盘。

---

## 开发路线图

> **目标**：开源、配置驱动的 PMSM 建模、多工具联合仿真、故障注入与可复现仿真实验框架。

### 愿景

研究者与工程师应当能用配置文件描述电机模型、运行工况、控制设置与故障场景，
然后执行一条可重复的仿真流程，而不必在多个工程软件里手工重建连接与设置。

框架整合：

- **Ansys Motor-CAD**：快速电机建模与等效电路导出
- **Ansys Maxwell**：有限元建模与 ECE 模型提取
- **Ansys Twin Builder (Simplorer)**：逆变器、电力系统与电机电路仿真
- **MATLAB/Simulink**：电机控制算法（FOC、SVPWM）与闭环控制

### 目标架构

```
                配置文件
     （电机 · 工况 · 故障 · 控制器与求解器设置）
                    │
                    ▼
              工作流编排
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
  Motor-CAD      Maxwell      故障场景
  ECE 导出     ECE 提取      与批量运行器
      │             │             │
      └─────────────┼─────────────┘
                    │
                    ▼
        Twin Builder / Simplorer
          （PMSM + 逆变器 + 功率级）
                    ↕
              MATLAB / Simulink
              （FOC–SVPWM 控制）
                    │
                    ▼
            仿真与数据导出
      （电流、电压、转速、转矩、故障标签）
```

图中是**目标架构**，完整端到端流程尚未发布。

### 当前状态

| 组件 | 状态 | 范围 |
|---|---|---|
| Motor-CAD ECE 导出 | 已实现，持续验证中 | 自动化 ECE 数据/模型导出与参数提取 |
| Maxwell ECE 提取 | 已实现，持续验证中 | 脚本化 Maxwell ECE 准备与提取流程 |
| Twin Builder–Simulink 模型绑定 | 已实现，持续验证中 | 自动绑定并生成对应 Simulink 模型 |
| Twin Builder (Simplorer) + Simulink 联合仿真自动化 | 开发中 | 自动化功率系统与控制系统的耦合 |
| 配置驱动的 PMSM 故障仿真套件 | 开发中 | 故障设置、批量场景、仿真运行与结果导出 |

「已实现」指仓库中有可用的代码与文档，**不代表**每个环境、模型或工况都已验证。

### 里程碑

#### M1 — 现有自动化工具

**状态**：已实现，持续改进中。

- [x] Motor-CAD ECE 导出命令行与文档
- [x] Maxwell ECE 提取流程与命令行
- [x] Twin Builder–Simulink 模型绑定自动化
- [x] 初始单元测试与示例配置
- [ ] 扩展兼容性测试，改进错误报告
- [ ] 建立不依赖商业软件的 CI 检查

#### M2 — Twin Builder (Simplorer) + Simulink 联合仿真

**状态**：开发中。设计已完成，尚无实现代码。

- [ ] 定义功率与控制系统耦合模型的配置结构
- [ ] 自动化 Twin Builder 电路/工程搭建与 Simulink 控制器绑定
- [ ] 支持 FOC–SVPWM 闭环仿真配置
- [ ] 在软件 API 支持的范围内，自动化求解器设置、信号交换配置与运行执行
- [ ] 验证典型稳态与动态转速/负载工况
- [ ] 导出同步的仿真输出与运行元数据

**通过标准**：有文档化的样例，能从配置文件跑通 PMSM 功率系统/控制系统耦合仿真，
并清晰报告结果与失败。

#### M3 — 配置驱动的 PMSM 故障仿真套件

**状态**：开发中。资料调研阶段。

- [ ] 定义电机、故障、严重程度、工况与输出设置的版本化结构
- [ ] 在模型与 API 允许的范围内实现故障专用适配器
- [ ] 覆盖代表性故障类别：匝间短路、绕组开路、退磁、偏心、逆变器开关管开路
- [ ] 提供转速、负载、故障严重程度与噪声条件的参数扫描
- [ ] 自动化场景执行、日志记录与结构化数据导出
- [ ] 保留故障标签、配置快照、软件版本与运行标识，保证可复现

**通过标准**：用户能通过配置指定至少一种已验证的故障类型与多个工作点，
执行支持的运行，并获得带标签的数据与可复现的运行记录。

> **安全与范围**：故障实现与物理保真度取决于底层电机模型与仿真器。
> 高风险或不支持的故障工况，不能仅凭自动化就假定已经验证。

#### M4 — 可靠性、文档与社区采用

**状态**：规划中。

- [ ] 增加端到端示例工程，明确写出前置条件
- [ ] 扩充离线单元与回归测试，并为有许可的软件环境提供可选的集成测试
- [ ] 记录软件版本兼容性与已知限制
- [ ] 增加贡献指南、Issue 模板与发布流程
- [ ] 发布带更新日志与验证说明的版本标签
- [ ] 通过 Issue、讨论与贡献收集真实社区反馈

### 为什么分阶段推进

闭环联合仿真需要先有稳定的电机侧模型。三个已发布工具产出的 ECE 模型正是这个输入。
先把电机侧做扎实，再往上搭功率级与控制级，避免两边同时不确定——
出问题时能立刻定位到哪一层。

> 破坏对称性的故障（偏心、局部退磁、磁钢碎裂）必须用 **Full Machine（360° 完整模型）**，
> 因为半模型无法表达非对称场。这是本项目的硬约束。

### 参与贡献

欢迎在 Python 自动化、测试覆盖、配置校验、错误诊断、文档与可复现仿真示例方面参与贡献。
涉及集成类的改动，请注明使用的 Ansys 与 MATLAB/Simulink 版本，
并区分「在商业软件中验证的结果」与「仅离线测试的结果」。

### 依赖与限制

- 本仓库的自动化代码开源，但 **Ansys 与 MATLAB/Simulink 是商业软件**，集成与仿真需要相应许可
- 自动化的支持范围与求解器行为会随软件版本、模型与环境变化
- 里程碑描述的是计划中的工作，不构成对功能或交付时间的承诺
- AI 辅助的贡献在作为受支持功能之前，须经过审查与验证

### 状态更新

进展通过仓库提交、Issue、Pull Request 与 Release 跟踪。
功能实现并验证后，本路线图会同步更新。

---

## 贯穿案例：BMW i3 (e11) IPM 电机

仓库里的模型与配置都围绕这台电机：

| 参数 | 值 |
|---|---|
| 极数 / 极对数 | 8 / 4 |
| 定子外径 | 198 mm |
| 槽数 | 48 |
| 每槽导体数 / 每导体匝数 | 108 / 6 |
| 并联支路 | 2 |
| 相电阻 Rs | 13.377 mΩ |
| 永磁磁链 λpm | 0.075883 Wb |
| Ld（额定点 / 饱和端） | 231.8 / 226.3 µH |
| Lq（额定点 / 饱和端） | 382.7 / 297.4 µH |
| 凸极率 | 1.65 |
| 母线电压 | 400 V |
| 峰值电流 | 433 A |

由 ECE 数据反推的控制参数（`dist/ece-export/scripts/calc_control_params.py` 可重算）：

| 参数 | 值 |
|---|---|
| MTPA 工作点（实测最优点） | Id = −303.1 A，Iq = 303.1 A → 246.4 N·m |
| 电流环 Kp_d / Ki_d | 1.456 / 84.05 |
| 电流环 Kp_q / Ki_q | 2.405 / 84.05 |
| 各转速可达转矩 | 4000 rpm: 246 N·m · 6000 rpm: 195 N·m · 10000 rpm: 106 N·m |

> 电感按**磁链反推**（`Lq = λq/iq`、`Ld = (λd − λpm)/id`），不直接取 MAT 里的 `Ld`/`Lq` 字段——
> 后者在零电流处是除零产物，量纲与标称不符。

模型样例：

```
models/
├── motorcad/e11_User.mot           Motor-CAD 模型（Full Machine 状态）
└── aedt/E11_FULL/e11_PMSM_IPM.aedt Maxwell 2D，含 PMSM_Healthy + PMSM_UD 两个 design

dist/maxwell-ece/models/e11_PMSM_IPM.aedt   工具 3 自带的同一份工程
```

---

## 目录结构

```
ansys-simulink-pmsm-cosimulation/
├── dist/                       可独立取用的自包含工具包
│   ├── simulink-binding/       工具 1：Twin Builder ⇄ Simulink 绑定
│   ├── ece-export/             工具 2：Motor-CAD ECE 导出
│   └── maxwell-ece/            工具 3：Maxwell 原生 ECE 提取
├── src/
│   ├── motorcad_controller/    Motor-CAD 控制
│   ├── simulink_controller/    Simulink 绑定
│   └── data_exchange/          .aedt 解析与数据模型
├── scripts/                    命令行入口
├── config/                     配置
├── models/                     电机模型样例
└── tests/                      单元测试
```

---

## 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.12 | 建议 conda 环境 |
| ansys-motorcad-core | 0.8.8 | Motor-CAD 控制 |
| pyaedt | 1.4.0 | AEDT 控制（导入路径 `ansys.aedt.core`） |
| matlabengine | 24.2 | 配 MATLAB R2024b |
| AEDT | 2026 R1 | 含 Maxwell 2D/3D、Twin Builder |
| Motor-CAD | 2026 R1 | |
| MATLAB | R2024b | |

许可服务器地址按本机环境配置（`ANSYSLMD_LICENSE_FILE`），不写进仓库。

---

## 快速开始

```powershell
# 1. 装依赖
conda create -n pmsm python=3.12
conda activate pmsm
pip install ansys-motorcad-core==0.8.8 pyaedt==1.4.0 matlabengine==24.2

# 2. 跑单测（不需要安装 Ansys / MATLAB）
python -m pytest tests/ -q

# 3. 各工具单独使用，见其 README
```

---

## 一点说明

这些工具是在真实工程里**撞出来的**，不是先设计好再实现。所以代码和 README 里保留了大量实测记录：

- 某个 API 不能用、换哪条路能用
- 某个参数填错会导致什么后果（比如网格必须含 0 A）
- 某条路试过但失败，为什么放弃

它们对后来者比结论本身更有用——同样的坑不必再踩一遍。

---

## 授权

本仓库代码用于电机仿真自动化研究。模型数据（BMW i3 电机参数）来自公开资料。
Ansys 与 MATLAB 为商业软件，需自行取得许可。
