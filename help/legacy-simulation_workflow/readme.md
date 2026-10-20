# PMSM 多域联合仿真自动化平台 — 技术方案

**Motor-CAD + Maxwell + Simplorer (Twin Builder) + MATLAB Simulink 联合仿真，Python 全流程自动化，支持 PMSM 故障注入**

> 命名说明：Ansys AEDT 自 **2021R2** 起将 Simplorer 更名为 **Twin Builder**（功能与工程文件格式兼容延续）。本方案中"Simplorer / Twin Builder"指同一工具，下文统一简称 **TB**。

---

## 目录

1. [项目概述](#1-项目概述)
2. [总体架构](#2-总体架构)
3. [技术栈与环境要求](#3-技术栈与环境要求)
4. [核心工作流](#4-核心工作流)
5. [联合仿真拓扑方案](#5-联合仿真拓扑方案)
6. [PMSM 故障注入设计](#6-pmsm-故障注入设计)
7. [数据流与接口设计](#7-数据流与接口设计)
8. [代码目录结构](#8-代码目录结构)
9. [实施路线图](#9-实施路线图)
10. [风险与对策](#10-风险与对策)
11. [附录：关键 API 速查](#11-附录关键-api-速查)

---

## 1. 项目概述

### 1.1 背景与目标

PMSM（永磁同步电机）驱动系统涉及**快速设计（Motor-CAD）— 电磁场（Maxwell）— 电路（Simplorer/TB）— 控制（Simulink）**四个环节。传统手工操作流程繁琐、难以批量复现，且故障注入（断相、匝间短路、退磁等）场景众多，逐个手工搭建成本极高。

本项目目标：

1. **建模自动化**：先用 Motor-CAD（PyMotorCAD）完成 PMSM 快速建模与电磁初算，再自动导入 Maxwell（PyAEDT）建立精细 FEM 模型并求解，导出磁链、转矩、反电动势等特性；
2. **多域联合仿真**：打通 Maxwell ↔ Simplorer/TB ↔ Simulink，实现电磁—电路—控制闭环；
3. **故障注入**：以"场景矩阵"方式批量注入电气/电磁/机械/传感器类故障，量化故障特征；
4. **一键编排**：场景配置（YAML）→ 自动调度 → 结果采集 → 指标对比 → 生成报告，全程无需人工干预。

### 1.2 范围

| 包含 | 不包含（远期） |
| --- | --- |
| Motor-CAD PMSM 快速建模、电磁初算、性能地图/dq 磁链图导出 | 3D 电磁场精细化建模（接口可扩展） |
| Maxwell 2D PMSM 电磁建模与瞬态求解（自动导入 Motor-CAD 几何/参数） | Motor-CAD 热/结构快速评估（TM/DM 模块） |
| TB 驱动电路（VSI 逆变器 + 电机耦合） | 热/结构场耦合 |
| Simulink FOC 控制模型与联合仿真 | 多机并行调度 |
| 电气 / 电磁 / 机械 / 传感器四类故障注入 | 优化算法闭环（DOE/寻优） |
| 批量场景编排、结果对比与 HTML 报告 | 云部署 |

### 1.3 方案假设

- 目标电机：**表贴式/内置式 PMSM**，额定功率 ≤ 数十 kW 量级（参数可配置）；
- 运行环境：**Windows 10/11 x64**（AEDT 与 MATLAB Engine 均为 Windows 限定）；
- 控制策略以 **FOC（磁场定向控制）** 为主线，SVPWM 调制；
- Motor-CAD、AEDT 与 MATLAB 均安装在**同一台机器**（自动化走 COM / 本地进程间通信）。

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python 自动化编排层 (orchestrator)              │
│    场景矩阵(YAML) → 流程调度 → 参数下发 → 状态管理 → 结果采集 → 报告  │
└───────────────┬──────────────────────────────┬──────────────────┘
                │ PyAEDT / PyMotorCAD          │ matlabengine
┌───────────────▼──────────────┐  ┌────────────▼─────────────────┐
│ Motor-CAD (独立应用)          │  │ MATLAB / Simulink            │
│ · PMSM 快速建模(尺寸/材料/绕组)│  │ ┌──────────────────────────┐ │
│ · 电磁初算/性能地图/dq 磁链图  │  │ │ 控制层 (FOC)             │ │
│ · 退磁/偏心参数初筛           │  │ │ · Clarke/Park · PID      │ │
└───────┬──────────────────────┘  │ │ · SVPWM · 传感器故障注入  │ │
        │ 几何/参数/磁链数据导出    │ └────────────┬─────────────┘ │
┌───────▼──────────────────────┐  │              │ S-function     │
│ AEDT (Ansys Electronics     │  │              │ 联合仿真(双向)  │
│       Desktop)               │  │              │                │
│ ┌─────────────────────────┐ │  │              │                │
│ │ Maxwell 2D: PMSM 电磁建模│ │  │              │                │
│ │ 几何/材料/绕组/激励/求解  │ │  │              │                │
│ │ 故障: 退磁/偏心/磁钢碎裂  │ │  │              │                │
│ │ 输出: 磁链/转矩/反电动势  │ │  │              │                │
│ └───────────┬─────────────┘ │  │              │                │
│             │ MSML/等效模型导出│ │              │                │
│ ┌───────────▼─────────────┐ │◄─┼──────────────┘                │
│ │ Twin Builder (Simplorer)│ │  │                               │
│ │ 电机耦合/逆变器/驱动电路  │ │  │                               │
│ │ 电气故障注入(开关/短路)  │ │  │                               │
│ └─────────────────────────┘ │  │                               │
└─────────────────────────────┘  └───────────────────────────────┘
```

**分层职责**

| 层 | 模块 | 职责 |
| --- | --- | --- |
| 编排层 | `orchestrator.py` | 读配置、建场景矩阵、串行调度各阶段、断点续跑、汇总结果 |
| Motor-CAD 控制层 | `motorcad_client.py` | Motor-CAD 快速建模、电磁计算、几何/磁链数据导出 |
| AEDT 控制层 | `maxwell_controller.py` | Maxwell 建模/参数化/求解/结果导出 |
| | `twinbuilder_controller.py` | TB 电路搭建、耦合组件配置、求解 |
| | `faults.py` | 三类故障注入的具体实现（参数、电路开关、几何） |
| MATLAB 控制层 | `matlab_client.py` | Engine 生命周期、模型加载、参数下发、运行、结果回读 |
| 数据层 | `io.py` | YAML 场景解析、CSV/MAT 读写、指标计算、报告生成 |

---

## 3. 技术栈与环境要求

### 3.1 软件版本矩阵

| 软件 | 建议版本 | 本机实测 | 说明 |
| --- | --- | --- | --- |
| Ansys AEDT | 2023R2 及以上 | **2026 R1 (26.1)** | `F:\ANSYS Inc\v261\AnsysEM`；Maxwell 2D/3D + Twin Builder/Simplorer + `MaxwellSimulink.dll`（Simulink 耦合库）齐备 |
| Ansys Motor-CAD | 2023R2 及以上 | **2026R1** | `F:\ANSYS Inc\v261\motorcad`，与 AEDT 同一版本树 |
| MATLAB / Simulink | R2022b 及以上 | **R2024b (24.2)** | `C:\Program Files\MATLAB\R2024b`；Simulink 工具箱已确认在位 |
| Python | 3.9 – 3.12 | **3.11.15**（conda env `pyaedt`） | 环境路径 `C:\Env\anaconda3\envs\pyaedt` |
| PyAEDT | 最新稳定版 | **1.2.0** | 1.x 起导入名改为 `ansys.aedt.core`（见 §3.3） |
| PyMotorCAD | 最新稳定版 | **ansys-motorcad-core 0.8.6** | 导入名 `ansys.motorcad.core` |
| MATLAB Engine | 与 MATLAB 版本配对 | **24.2**（已安装） | R2024b 配对版本，M0 已验证可用 |
| 其他 Python 库 | — | — | `pyyaml pandas numpy matplotlib jinja2` |

### 3.2 关键软件组件说明

- **PyAEDT**：Ansys 官方开源客户端，直接驱动 AEDT 内部 API（COM）。支持 `Maxwell2d`、`Rmxprt`、`TwinBuilder` 等对象，支持无界面（`non_graphical`）批处理模式 —— 这是自动化批量跑场景的基础。**注意**：PyAEDT **1.x 起导入名改为 `from ansys.aedt.core import ...`**（本机 1.2.0 实测已无 `pyaedt` 顶层包，官方文档同步使用新命名空间）。
- **PyMotorCAD（包名 `ansys-motorcad-core`）**：Ansys 官方 Python 客户端，封装 Motor-CAD 的 COM 接口；支持打开/参数化 `.mot` 工程、运行电磁计算、导出几何与磁链数据 —— S1 自动化的基础。本机已装 0.8.6，导入名 `ansys.motorcad.core`。
- **MATLAB Engine API for Python**：官方支持的跨语言接口，`eng.sim()` 可同步/异步运行 Simulink 模型，`set_param` 下发参数，`eval` 执行任意 MATLAB 命令。
- **MSML（Maxwell to Simplorer Model Library）**：Maxwell 导出供 TB 耦合的电机组件文件；TB 中通过 "Ansys Maxwell Component" 实现 FEM–电路联合仿真。

### 3.3 本机环境实测（2026-08-02 自动探查）

| 项 | 实测值 |
| --- | --- |
| conda 环境 `pyaedt` | `C:\Env\anaconda3\envs\pyaedt`（Python 3.11.15，conda-forge） |
| pyaedt 1.2.0 | 可用；导入名 `ansys.aedt.core`（`Maxwell2d`/`TwinBuilder` 导入已验证） |
| ansys-motorcad-core 0.8.6 | 可用；导入名 `ansys.motorcad.core`（已验证） |
| matlabengine | **24.2** 已安装 | 导入 `matlab.engine` 已验证；Engine 实际启动成功（release=2024b） |
| AEDT 2026 R1 | `F:\ANSYS Inc\v261\AnsysEM`，含 Maxwell 2D/3D、Simplorer/Twin Builder、`MaxwellSimulink.dll`（Simulink 联合仿真接口库）、`DigitalTwinFitting.dll`（ROM/数字孪生） |
| Motor-CAD 2026R1 | `F:\ANSYS Inc\v261\motorcad\MotorCAD.exe`；`MOTORCAD_ACTIVEX` 环境变量已配置（COM 自动化入口就绪） |
| MATLAB R2024b | `C:\Program Files\MATLAB\R2024b`；Simulink 及 Simulink Coder 系列工具箱在位 |
| 许可 | Ansys PLE Licensing 2026 R1 服务运行中，`ANSYSLMD_LICENSE_FILE=1055@localhost`；**M0 实际启动验证通过**：AEDT（gRPC 会话）、Motor-CAD（RPC 实例）、MATLAB Engine 均连接成功 |
| 环境变量 | `ANSYSEM_ROOT261`、`AWP_ROOT261`、`ANSYS261_DIR`、`SIMPLORER_HOME` 均已设置；**注**：`ANSYS261_DIR` 指向 `F:\ANSYS Inc\v261\ANSYS`（该目录不存在，疑为遗留变量，未被 pyaedt 使用；实际生效入口为 `ANSYSEM_ROOT261`/`AWP_ROOT261`） |
| M0 验证门 | **2026-08-04 门禁全绿(exit 0)**:Motor-CAD 12.6s / MATLAB Engine 14.6s / AEDT gRPC 17.7s;`scripts/check_env.py` 已落地。**MEX 编译器(二次标定 2026-08-04 晚)**:VS 2022 Community 已安装并被 MATLAB R2024b 识别,`mex.getCompilerConfigurations('C','Installed')`=2(MinGW64 + Microsoft Visual C++ 2022);**默认编译器已切为 MSVC 2022**(官方支持版本,经 `mex -setup C` 在临时移除 `MW_MINGW64_LOC` 后选定,持久化于 prefdir `mex_C_win64.xml`);`MW_MINGW64_LOC=F:\Env\mingw64` 恢复保留,MinGW gcc 15.2 作为备选 |

---

## 4. 核心工作流

整体流程按 7 个阶段顺序执行（S0 可独立验证）：

```
S0 环境检查 → S1 Motor-CAD 快速建模 → S2 Maxwell 电磁建模
           → S3 TB 电路搭建 → S4 Simulink 控制耦合
           → S5 故障注入(场景矩阵) → S6 批量运行 + 结果采集 + 报告
```

### S0 环境检查（一次性的验证门）

- 启动 AEDT（图形/无界面）并新建空工程成功；
- 启动 Motor-CAD（PyMotorCAD COM 连接）并打开/保存一个模板工程成功；
- 启动 MATLAB Engine 并运行 `sim` 一个 demo 模型成功；
- 验证 MEX 编译器可用（`mex -setup`），确保后续 S-function 能编译；
- 将版本信息、许可状态写入 `results/env_report.json`。

### S1 Motor-CAD 快速建模

作为整条链路的**起点**：数分钟内完成 PMSM 快速尺寸方案与电磁初算，为后续 FEM、电路、控制提供参数与数据基线。

1. 模板与参数化：加载 `models/motorcad/` 下的 `.mot` 模板，按 `config/cases.yaml` 参数化（极槽配合、尺寸、材料、绕组、磁钢）；
2. 电磁计算：运行 Motor-CAD EMag 计算，输出转矩/转速曲线、效率地图、dq 磁链图（flux map）；
3. 数据导出（两个方向）：
   - **→ Maxwell**：一键导出几何/材料/绕组至 Maxwell 2D，免去手工重建（S2 的输入）；
   - **→ TB / Simulink**：导出 dq 磁链图/性能数据，直接供 TB 等效电机模型与 Simulink 查表模型使用（方案 B 的等效模型数据源）；
4. 故障初筛：退磁比例、偏心率等**参数级故障**在 Motor-CAD 层秒级~分钟级快速扫描，粗筛后再进 Maxwell 精细验证；
5. 工程归档：每次运行的 `.mot` 与导出文件写入 `results/motorcad/<batch>/`。

### S2 Maxwell 电磁建模

建模走两条路线（可在配置中切换）：

| 路线 | 方式 | 适用 |
| --- | --- | --- |
| 快速路线 | **Motor-CAD 几何/参数一键导出**，自动带入 Maxwell 2D（或 RMxprt 参数化） | 标准电机，快速获得 FEM 模型 |
| 直接路线 | 脚本直接构建 Maxwell 2D 几何（定子/转子/磁钢/绕组） | 需要精细控制几何的故障场景（偏心、磁钢碎裂） |

自动化内容：

1. 几何与材料：参数化设计变量（如 `Br`、`Hc`、气隙、磁钢厚度、偏心量）；
2. 绕组与激励：相绕组设置、激励类型（外电路/电流源）、运动设置（Motion，转速或负载）；
3. 网格与求解：自动网格划分（`mesh.assign_length_mesh` 等），`Transient` 求解；
4. 结果导出：转矩-时间、三相反电动势、磁链、电感；导出 MSML 组件或等效电路参数供 S3 使用。

> 故障接口预留：退磁（改 `Br`/`Hc`）、偏心（几何偏移变量）、磁钢碎裂（磁体分段剔除）均在建模阶段以**参数**形式暴露。

### S3 Twin Builder (Simplorer) 电路搭建

1. 放置**电机耦合模型**：方案 A 用 Ansys Maxwell 耦合组件（MSML，绑定 S2 的 Maxwell 工程）；方案 B 用 Motor-CAD/Maxwell 导出的 dq 磁链图等效模型；
2. 搭建驱动电路：直流母线 → 三相 VSI 逆变器（IGBT + 反并联二极管）→ 电机三相端；
3. 控制接口：占空比/门极信号或电流指令端口，留作 S4 Simulink 联调；
4. 电气故障注入电路（详见 §6）：在每一相串联/并联可控开关与短路支路；
5. 求解器设置：步长（`1e-5` 量级）、停止时间，与 S4 采样率匹配。

### S4 Simulink 控制耦合

1. 建立 FOC 控制模型：转速外环（PI）+ d/q 轴电流内环（PI）+ Clarke/Park 变换 + SVPWM；
2. 接入 TB 联合仿真接口：使用 TB 生成的 S-function 模块（详见 §7.1）；
3. Python 侧通过 `set_param` 下发控制参数（PID 增益、给定转速、负载）；
4. 闭环联合仿真：验证转速跟踪、电流波形、稳态精度，记录基线（healthy）结果。

### S5 故障注入（场景矩阵）

读取 `config/cases.yaml`，将每个场景展开为"故障类型 + 注入时刻 + 严重度 + 负载条件"元组，按场景逐个注入并仿真（详见 §6）。

### S6 批量运行、采集与报告

1. 逐场景运行联合仿真（串行，避免许可与进程冲突）；
2. 采集波形（转速/转矩/相电流/母线电压）与指标（详见 §6.3）；
3. 与 healthy 基线自动对比，生成指标差异表；
4. 输出 HTML 报告（波形图 + 指标表 + 故障特征摘要）至 `results/reports/`。

---

## 5. 联合仿真拓扑方案

三种拓扑按**精度—速度**权衡选择：

| 方案 | 耦合方式 | 精度 | 速度 | 适用 |
| --- | --- | --- | --- | --- |
| **A 全耦合** | Maxwell FEM ↔ TB 电路 ↔ Simulink 控制三方实时联合 | ★★★ | 慢 | 关键工况验证、故障机理研究 |
| **B 两步法（推荐主线）** | 先离线求解并导出**等效模型/ROM**（dq 磁链图、电感、反电动势）——数据源可为 Motor-CAD（最快）或 Maxwell（更精确）；TB 中使用等效电机模型，再与 Simulink 耦合 | ★★☆ | 快 | 故障批量扫描、控制策略验证 |
| **C 离线数据链** | 各工具独立运行，结果以文件（CSV/MAT）传递，Simulink 用查表/数据驱动模型 | ★☆ | 最快 | 参数敏感性初筛、回归测试 |

**建议策略**：链路起点用 Motor-CAD 完成快速建模与参数初筛；批量故障扫描走 **方案 B**（等效模型保证速度与可复现性，数据源优先取 Motor-CAD dq 磁链图）；对需要精确场效应（局部退磁、偏心）的场景走 **方案 A** 复算验证。两种模式由配置文件 `co_sim.mode` 切换，编排层只面向统一接口，不感知拓扑差异。

---

## 6. PMSM 故障注入设计

### 6.1 故障分类与注入矩阵

| 类别 | 故障 | 注入层级 | 实现方式 | 关键参数 |
| --- | --- | --- | --- | --- |
| 电气 | 断相（开路） | TB 电路 | 相绕组串联可控开关，`t_fault` 时刻断开 | 故障相、时刻 |
| 电气 | 相间短路 | TB 电路 | 两相之间加短路支路（小电阻 + 开关） | 相别、短路电阻、时刻 |
| 电气 | 匝间短路 | TB 电路 | 绕组**分段建模**（如 90%+10%），10% 段经短路电阻 + 开关接入 | 匝比（严重度）、短路电阻、时刻 |
| 电气 | 对地短路 | TB 电路 | 绕组端经电阻 + 开关接地 | 相别、接地电阻、时刻 |
| 电气 | IGBT 开路/短路 | TB 电路（逆变器） | 每只功率管并联/串联故障开关 | 管号、类型、时刻 |
| 电磁 | 整体/局部退磁 | Maxwell 材料 | 参数化 `Br`/`Hc`（整体）；磁体分区后改局部材料（局部退磁） | 退磁比例、区域 |
| 电磁 | 静/动偏心 | Maxwell 几何 | 转子/转轴偏移参数化（静态固定偏移 / 动态旋转偏移） | 偏心比例、类型 |
| 电磁 | 磁钢碎裂/错位 | Maxwell 几何 | 磁体分段建模，移除/偏移某段 | 碎裂段、位置 |
| 机械 | 负载突变/堵转 | Simulink | 负载转矩阶跃/斜坡/常值（堵转） | 负载值、时刻 |
| 机械 | 轴承摩擦增大 | Simulink | 摩擦系数/库仑力矩参数 | 摩擦系数 |
| 传感器 | 位置/电流传感器故障 | Simulink | 信号通道加增益偏差、偏置、噪声、失效（饱和） | 传感器、偏差类型、幅值 |

### 6.2 三种注入实现方式

1. **参数化注入**（改设计变量后重新求解）：退磁、偏心、负载、传感器偏差 —— 由 Python 修改 Motor-CAD/Maxwell/Simulink 参数并重跑，适合批量扫描；退磁与偏心率采用**两级流水线**：Motor-CAD 快速初筛 → Maxwell 精细验证；
2. **电路开关注入**（仿真中途动作）：断相、相间短路、匝间短路、IGBT 故障 —— 在 TB 电路里预置故障支路与可控开关，Python 设置开关动作时刻，无需重建电路；
3. **几何重建注入**（模型级）：磁钢碎裂、错位 —— 修改几何后重新求解（耗时最长，仅用于方案 A 关键场景）。

> 工程要点：**匝间短路**是把绕组拆分为串联两段、用"短路电阻 + 开关"旁路其中一段实现的，匝比决定故障严重度——这是 TB 电路中最常用也最需要精细化的故障模型。

### 6.3 结果指标

- **正常运行指标**：转速/转矩跟踪误差、电流 THD、效率、转矩脉动系数；
- **故障特征指标**：故障相电流幅值/畸变、负序电流分量、转矩波动幅度、退磁后反电动势降幅、故障后到达稳态的过渡时间；
- 所有指标由 `io.py` 统一计算，healthy 基线自动对比，超阈值自动告警（阈值在 YAML 配置）。

---

## 7. 数据流与接口设计

### 7.1 实时联合仿真接口

| 接口 | 方向 | 机制 |
| --- | --- | --- |
| Maxwell → TB | 单向 | MSML 耦合组件 / 等效模型导出文件 |
| TB ↔ Simulink | **双向** | TB 的 *Simulink Co-Simulation* 组件自动生成 **S-function（MEX）**，Simulink 中通过对应模块接入；本地进程间通信（Windows COM/共享内存），固定采样步长 |

> 注意：S-function 接口与 **AEDT 版本、MATLAB 版本强相关**，版本不匹配是联合仿真失败的首要原因——必须在 M0 验证门一次性确认，并锁定版本组合写入 `config/base.yaml`。

### 7.2 批间数据交换

| 数据 | 格式 | 用途 |
| --- | --- | --- |
| 场景定义 | YAML | 电机参数、拓扑模式、故障场景矩阵 |
| 电机设计数据 | .mot / CSV | Motor-CAD 工程与导出的 dq 磁链图/性能地图，供 Maxwell 建模与 TB 等效模型 |
| 波形结果 | CSV / MAT | 转矩、转速、相电流、电压等时序数据 |
| 指标结果 | JSON / CSV | 各场景指标汇总，供对比与报告 |
| 波形图/报告 | PNG / HTML | 可视化与交付 |

### 7.3 场景配置示例（`config/cases.yaml`）

```yaml
motor:
  type: "surface_pmsm"          # surface_pmsm / interior_pmsm
  pole_pairs: 4
  slots: 24
  rated_power_kw: 1.5
  rated_speed_rpm: 1500
  dc_bus_v: 311

co_sim:
  mode: "twinbuilder_simulink"  # A 全耦合 / B 等效模型 / C 离线
  sample_time_s: 1e-5
  stop_time_s: 2.0

scenarios:
  - name: "healthy"                     # 基线
    fault: none
  - name: "phase_a_open"                # A 相断相 @0.5s
    fault: { type: "phase_open", phase: "A", time_s: 0.5 }
  - name: "interturn_short_10pct"       # A 相 10% 匝间短路 @0.5s
    fault: { type: "interturn", phase: "A", ratio: 0.1, r_short_mohm: 50, time_s: 0.5 }
  - name: "demag_20pct"                 # 整体退磁 20%
    fault: { type: "demagnetization", mode: "global", br_ratio: 0.8 }
  - name: "eccentricity_static_20pct"   # 20% 静偏心
    fault: { type: "eccentricity", mode: "static", ratio: 0.2 }
  - name: "load_step"                   # 0.5s 负载阶跃至 150%
    fault: { type: "load_step", value_ratio: 1.5, time_s: 0.5 }
```

---

## 8. 代码目录结构

```
simulation_workflow/
├── readme.md                    # 本方案
├── help_md/                     # AEDT / Motor-CAD 官方帮助文档（Markdown 导出，见下）
├── templates/
│   └── motorcad/                # 手工 .mtt 模板（如 e7_eMobility_SPM_20kW.mtt）
├── config/
│   ├── base.yaml                # 全局配置（版本、路径、许可、阈值）
│   └── cases.yaml               # 电机参数 + 故障场景矩阵
├── src/
│   ├── orchestrator.py          # 主编排：场景矩阵调度、状态管理、断点续跑
│   ├── motorcad_controller/
│   │   └── motorcad_client.py       # S1：Motor-CAD 快速建模/计算/导出
│   ├── aedt_controller/
│   │   ├── maxwell_controller.py    # S2：Maxwell 建模/求解/导出
│   │   ├── twinbuilder_controller.py# S3：TB 电路/耦合/求解
│   │   └── faults.py                # 故障注入实现（参数/开关/几何）
│   ├── simulink_controller/
│   │   └── matlab_client.py         # S4：Engine 封装（启动/下发/运行/回读）
│   └── data_exchange/
│       ├── io.py                    # YAML/CSV/MAT 读写、指标计算
│       └── report.py                # HTML 报告生成
├── models/                      # 自动生成的工程文件（脚本产物，不入库）
│   ├── motorcad/                 # 由 templates/ 模板生成的 .mot 工程
│   ├── maxwell/
│   ├── twinbuilder/
│   └── simulink/
├── scripts/
│   ├── check_env.py             # S0 环境验证门
│   └── run_all.py               # 一键入口
├── results/                     # 输出（波形、指标、报告），按运行批次分目录
└── tests/                       # 单元/集成测试（配置解析、指标计算等）
```

> **`help_md/`**：Ansys AEDT 与 Motor-CAD 官方帮助文档的 Markdown 导出，共 26 个主题目录，包括 Maxwell/Twin Builder/Motor-CAD 脚本指南（`MaxwellScriptingGuide`、`Twin BuilderScriptingGuide`、`CircuitScriptingGuide`）、联合仿真教程（`Motor-CAD_FMU_Tutorial`、`Simplorer_BLACMotorControlSystem`、`TwinBuilder_ECE_Tutorial`、`MATLAB_Simscape_Export_BPM` 等）及组件/导出参考（`Ansys_Maxwell_Export`、`Basic Elements`、`Power System` 等）。这是自动化脚本 API 用法的一手参考资料，实施各模块前优先查阅对应主题。

---

## 9. 实施路线图

| 里程碑 | 内容 | 验收标准（机器可验证） | 状态 |
| --- | --- | --- | --- |
| **M0 环境就绪** | 安装与版本锁定、许可确认 | `check_env.py` 通过：`ansys.aedt.core` 连接 AEDT 26.1 建空工程；`ansys.motorcad.core` 连接 Motor-CAD 并读写模板工程；`matlabengine` 已装且 Engine 启动并 `sim` 通 demo 模型；MEX 编译器可用 | ✅ **2026-08-04 门禁全绿(exit 0)**：三项工具实机启动 + Simulink 许可 + MEX 实测编译全部通过；MEX 编译器经 `MW_MINGW64_LOC` 指向本机 gcc 15.2.0 解决（见 `docs/verification-report-2026-08-04.md`） |
| **M1 Motor-CAD 快速建模** | PMSM 快速建模 + 电磁初算 + 数据导出 | 脚本自动生成 .mot 快速模型并完成电磁计算；导出 dq 磁链图/性能地图与 Maxwell 几何参数；结果与参考值误差在容差内 | ✅ **2026-08-04 代码落地并实机跑通**：`src/motorcad_controller/motorcad_client.py`（加载/参数化/EMag/导出/归档）+ `scripts/run_m1.py` + `config/base.yaml`+`config/cases.yaml`；实机全链路：加载 e11_User.mot → 参数化（activex 变量校验）→ EMag 计算 43.5s → 导出 Maxwell **full 脚本（SymmetryFactor=1）** → 归档 `results/motorcad/<batch>/`；单测 14/14；dq 磁链图/性能地图导出列入 M1b |
| **M2 Maxwell 建模** | PMSM 2D 参数化建模 + 瞬态求解 + 结果导出 | 自动导入 M1 的几何/参数生成 FEM 模型并求解；导出的转矩/磁链曲线与手工基线误差在容差内 | ✅ **2026-08-07 实机跑通**：`src/aedt_controller/maxwell_controller.py` + `scripts/run_m2.py`（纯 CLI：`ansysedt.exe -RunScriptAndExit` 执行 M1 脚本 → 求解 → 重建报告 → 导出 CSV → 归档）；**关键修复**：① 脚本执行走 CLI（pyaedt COM IDispatch 分派有怪癖、gRPC 无 ExecuteScript）；② 需开启气隙圆柱网格（`AnsysAirgapMesh=1`），否则求解报 "Edge is not preserved in the mesh"；③ 报告须在求解后重建（M1 脚本报告创建于求解前，为空壳）；实测导出 Torque（~200-215 Nm）与 Flux Linkage（PsiD/PsiQ）CSV |
| **M3 TB 电路** | 驱动电路 + 电机耦合（MSML 或磁链等效模型）+ 故障开关预置 | 电路联合仿真正常运行；断相/匝间短路开关可按指定时刻动作 | 待办 |
| **M4 Simulink 耦合** | FOC 控制 + S-function 联合仿真闭环 | 闭环稳定运行：转速收敛到给定值，电流波形正常，无数值发散 | 待办 |
| **M5 故障注入矩阵** | 四类故障参数化批量注入 | `cases.yaml` 全部场景一键跑通；各故障特征指标可提取并与健康基线对比 | 待办 |
| **M6 报告与回归** | 指标汇总、HTML 报告、基线自动对比 | 修改电机参数后重跑，基线对比表自动生成且差异可解释 | 待办 |

> 每个里程碑独立可交付、可回滚；M0 未通过前不进入后续阶段。

---

## 10. 风险与对策

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| AEDT 与 MATLAB 版本不匹配，S-function 接口异常 | 联合仿真无法建立 | M0 一次性验证并**锁定版本组合**；预留降级路径：方案 B/C（等效模型/离线）仍可完成批量任务 |
| License 并发不足 / 占用泄漏 | 任务阻塞、进程挂死 | 串行队列 + 超时控制 + 进程回收；脚本统一释放 Motor-CAD/AEDT/MATLAB 句柄；失败场景隔离不中断批次 |
| Motor-CAD COM 接口或许可异常 | S1 无法自动化 | M0 验证门覆盖 COM 连接；降级路径：手工导出的 .mot 模板 + 半自动参数替换 |
| `matlabengine` 未安装或版本与 MATLAB 不匹配 | 无法自动化 Simulink | M0 前置：`pip install matlabengine==24.2.*`（与 R2024b 配对）；版本锁定写入 `config/base.yaml` |
| PyAEDT 1.x 导入名变更（`ansys.aedt.core`） | 旧代码/旧文档示例报 ImportError | 全项目统一使用新命名空间；确需 `import pyaedt` 兼容时 `pip install pyaedt` 补装兼容入口 |
| S-function 编译环境缺失（缺 C 编译器） | 无法生成联合仿真接口 | M0 检查 `mex -setup`；CI 环境预装 VS Build Tools。**已解决（2026-08-04）**：先经 `MW_MINGW64_LOC` 启用本机 MinGW gcc 15.2 打通编译链；随后安装 VS 2022 Community，MATLAB 识别为官方支持编译器，**默认已切至 MSVC 2022**（`mex -setup C` 选定，持久化于 prefdir），MinGW 保留为备选 |
| Maxwell 瞬态求解耗时过长 | 批量效率低、总时长失控 | 主线用等效模型（方案 B）；仅关键场景跑 FEM（方案 A）；合理控制步长与停止时间 |
| 数值发散 / 求解不收敛 | 单场景失败拖垮批次 | 场景级 try/except + 断点续跑；收敛失败自动缩小步长重试一次 |
| PyAEDT 与 AEDT 版本不兼容 | API 报错 | 按官方兼容矩阵锁 PyAEDT 版本；升级前跑 M2 回归 |
| 批间数据格式漂移 | 结果解析失败 | 所有导出统一走 `io.py` 并带 schema 校验 |

---

## 11. 附录：关键 API 速查

> 以下为接口示意，具体签名以对应版本文档为准。

### 11.1 Motor-CAD（PyMotorCAD）

```python
# ansys-motorcad-core（PyMotorCAD 新包名；旧包名 pymotorcad）
# 注意：0.8.6 的正确导入名为类 MotorCAD（大写），`import motorcad` 不存在（2026-08-04 实测）
from ansys.motorcad.core import MotorCAD

mc = MotorCAD()                              # 启动/连接 Motor-CAD（COM/RPC）
mc.load_from_file(r"models/motorcad/template.mot")
mc.set_variable("Br", 1.2)                   # 修改设计变量（退磁初筛）
mc.do_magnetic_calculation()                 # 电磁计算
mc.save_to_file(r"results/motorcad/case01.mot")
# 几何→Maxwell 导出：export_to_ansys_electronics_desktop(file_path) 生成 VBS 脚本在 AEDT 中运行（0.8.6 实测存在）
# dq 磁链图/性能数据→TB/Simulink：API 待 M1b 定稿——注意 export_matrices() 导出的是 R/L/C 矩阵而非磁链图
```

### 11.2 PyAEDT — Maxwell 2D

```python
from ansys.aedt.core import Maxwell2d

m2d = Maxwell2d(project="pmsm", solution_type="Transient",
                design="Motion1", version="2023.2",
                non_graphical=True)      # 无界面批处理模式
# 注意：project 传纯工程名（如上）或带 .aedt 扩展名的完整路径；带路径但无扩展名会触发 OpenProject 失败（2026-08-04 实测）
m2d["Br"] = 1.2                          # 设计变量（退磁注入）
m2d["eccentricity"] = 0.0                # 偏心量参数
m2d.assign_coil(...)                     # 绕组/激励设置
m2d.mesh.assign_length_mesh(...)         # 网格
m2d.analyze("Setup1")                    # 求解
report = m2d.post.create_report("Torque")# 后处理
```

### 11.3 PyAEDT — Twin Builder (Simplorer)

```python
from ansys.aedt.core import TwinBuilder

tb = TwinBuilder(project="pmsm_tb", design="Drive", version="2023.2")
# 注意：0.8.6 无 add_design_variable，变量经 __setitem__/variable_manager 下发（2026-08-04 实测）
tb["R_short"] = "50mohm"                   # 短路电阻参数
tb["t_fault"] = "0.5s"                     # 故障时刻参数
# ... 放置 Maxwell 耦合组件、VSI、故障开关
# 注意：PyAEDT 未封装组件放置与 Simulink Co-Simulation 创建，需裸 AEDT COM/VBS 脚本（M3 主要工作量点）
tb.analyze()                               # 求解（替代不存在的 tb.solve()）
tb.export_results(...)                     # 结果导出（替代不存在的 export_report_csv）
```

### 11.4 MATLAB Engine — Simulink

```python
import matlab.engine

eng = matlab.engine.start_matlab()
eng.addpath(eng.genpath(r"models/simulink"), nargout=0)
eng.load_system("foc_control")

eng.set_param("foc_control/转速环/P", "Value", "5.0")   # 下发控制参数
out = eng.sim("foc_control", "StopTime", "2.0", nargout=1)  # 运行

eng.eval("data = logsout.getElement('torque').Values.Data", nargout=0)
torque = eng.workspace["data"]                 # 回读数据
eng.quit()
```

### 11.5 一键入口（示意）

```bash
python scripts/check_env.py     # M0 环境验证
python scripts/run_all.py       # 读 config/cases.yaml，跑全场景矩阵并出报告
```

---

*本文档为项目总体技术方案；各模块实现前，建议对 M1–M5 分别编写细化的设计说明与验收用例。*
