# e11 PMSM 控制模型 — 需求

## 1. 目标

为 `models/motorcad/e11_User.mot` 这台内置式永磁同步电机（IPM）建立 Simulink 侧的控制模型，电机本体与功率级放在 Twin Builder（Simplorer）侧。
第一阶段只做**参数整理 + ECE 提取**，控制模型搭建在参数与接口确认之后。

## 2. 背景

e11 是 Motor-CAD 的 eMobility 模板（同 e9 设计，转子开槽自适应模板），设计目标为 10,000 rpm、120 kW 级车用驱动。
项目已具备 Motor-CAD/Simulink 两侧的自动化能力，缺的是这台电机的控制侧参数与接口定义。

## 3. 功能点

### F1 电机基本参数整理

从 `.mot` 与 Motor-CAD 界面读出的参数，按控制模型需要的口径整理成一份可复核的清单：
电机类型、极槽配合、定子几何、转子磁钢、绕组形式与匝数、驱动设置、材料、额定工况点。

**验收**：每个参数带 `file:line` 坐标；无法从 `.mot` 直接读出的量（如每相匝数、d/q 电感、磁链）明确标注来源或「需实测」。

### F2 ECE 模型提取

用 Motor-CAD 的 ECE（等效电路提取）流程导出 e11 的 SML + TXT + MAT 三件套，供 Twin Builder 导入成 ECE 组件。

**验收**：产出 `ECE_e11_sml_file.sml` / `ECE_e11_txt_file.txt` / `ECE_e11_map.mat`；SML 的端口与引脚表与官方 ECE 定义一致。

### F3 控制模型接口定义

明确 Simulink 控制模型与 Twin Builder 功率级之间的输入输出信号，并据此搭建 e11 的 FOC + SVPWM 控制模型。

**验收**：接口表（信号名 / 方向 / 单位 / 物理含义）齐备；控制模型能在给定工况下输出三相电压指令、使用给定三相电流与转速反馈。

## 4. 边界

- 本阶段不做故障注入（偏心 / 局部退磁等），故障样机要求 Full Machine 的约束在此阶段不适用，但导出 Maxwell 时须遵守。
- 控制模型不包含功率器件模型：逆变器、母线电容、开关管在 Twin Builder 侧。
- MTPA 只做偏置表/查表形式的电流分配，不在此阶段做完整弱磁（MTPV）设计。

## 5. 依赖

| 依赖 | 版本 / 位置 |
|---|---|
| Motor-CAD | 2026 R1，`E:\ANSYS Inc\v261\motorcad` |
| ansys-motorcad-core | 0.8.8，conda `pmsm` |
| Twin Builder (AEDT) | 2026 R1 |
| MATLAB | R2024b |
| ECE 官方脚本 | `help/repos/pymotorcad/examples/links/ece_export_for_twinbuilder.py`（779 行，可运行版）<br>`E:\ANSYS Inc\v261\motorcad\Tutorials\Ansys_TwinBuilder_ECE_Model\MotorCAD_ECE_Export.py`（连接已开实例版） |

## 6. 待用户确认的设计选择

见 `docs/design/e11-control-model.md` §7——控制策略档位、弱磁范围、ECE 提取工况点三项。
