# Ansys-Simulink PMSM Cosimulation Scripts

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

**目标**：配置驱动的 PMSM 联合仿真自动化框架——
一份配置描述电机型号、故障类型与严重程度、转速/负载、控制器参数，整套流程自动跑完。

```
配置（电机 · 故障 · 工况 · 控制器）
        │
        ▼
Motor-CAD ECE → Maxwell ECE → Twin Builder 功率级 → Simulink 控制
        │
        ▼
    批量工况 · 数据导出
```

### 已发布（本仓库三个工具）

| 能力 | 位置 | 状态 |
|---|---|---|
| **Motor-CAD ECE 导出**<br>从 `.mot` 提取参数与等效电路 | `dist/ece-export` | ✅ 已发布 |
| **Maxwell ECE 提取**<br>有限元模型 → ECE3 + ECER | `dist/maxwell-ece` | ✅ 已发布 |
| **Simulink 绑定**<br>Twin Builder 模型与 Simulink 块绑定 | `dist/simulink-binding` | ✅ 已发布 |

三门工具各自独立可用，有命令行、退出码、单元测试。

> 「已发布」指工具本身可用且验证过冒烟，**不代表**所有版本、所有复杂工况都已覆盖。

### 开发中

| 能力 | 说明 | 当前进度 |
|---|---|---|
| **联合仿真自动化** | Twin Builder 功率系统（逆变器、母线）+ Simulink 控制系统（FOC/SVPWM/MTPA）串成一条可运行的闭环 | 设计已完成，尚未实现代码 |
| **PMSM 故障仿真套件** | 故障参数化配置 · 自动仿真 · 批量工况 · 数据导出 | 资料调研中 |

**故障类型规划**：

| 类别 | 故障 |
|---|---|
| 电磁 | 均匀退磁、局部退磁 |
| 电磁/机械 | 静态偏心、动态偏心 |
| 电气 | 定子绕组开路、匝间短路、相间短路 |

> 破坏对称性的故障（偏心、局部退磁、磁钢碎裂）必须用 **Full Machine（360° 完整模型）**，
> 因为半模型无法表达非对称场。这是本项目的硬约束。

### 为什么分两次做

闭环联调需要电机侧模型先稳定。三个已发布工具产出的 ECE 模型就是闭环的输入——
先把「电机侧」做扎实，再往上搭「功率级 + 控制级」，避免两边同时不确定、问题定位不到层。

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
