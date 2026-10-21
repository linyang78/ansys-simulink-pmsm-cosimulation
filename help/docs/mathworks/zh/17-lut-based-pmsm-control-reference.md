# LUT based PMSM Control Reference（模块）

> **MathWorks 官方文档存档（中文）**
> 来源：`https://www.mathworks.com/help/mcb/ref/lutbasedpmsmcontrolreference.html`（官方无中文翻译，以下为整理者翻译）
> 存档：2026-10-21 · R2026b · Since R2022b · 英文版：`en/17-lut-based-pmsm-control-reference.md`
> 库：Motor Control Blockset / Control / Synchronous Machine / Control Reference

---

## 描述

为 PMSM 的磁场定向控制生成基于查表的控制参考电流。

LUT based PMSM Control Reference 模块为永磁同步电机（PMSM）的磁场定向控制与弱磁控制生成
*d* 轴与 *q* 轴参考电流。输入参考转矩与反馈机械转速，模块输出对应的参考电流值。
模块支持最大转矩电流比（MTPA）与最大转矩电压比（MTPV）运行区。

模块使用 *id(T,ω)* 与 *iq(T,ω)* 查表生成参考电流值。
根据你指定电机参数的输入方式，模块可以自己生成查表，也可以使用你提供的数据。

### 电机参数输入方法

用 **Motor parameter input method** 参数指定下列之一：

**1. `Linear model with lumped parameters`（线性集中参数）**

用集中参数 *Ld*、*Lq*、*FluxPM* 计算 *id*/*iq* 查表。
模块通过求解与下列曲线相关的方程，得到给定 *ω* 和 *T* 时的 *id*、*iq*：

```
MTPA 曲线（IPMSM）： id² + id·ψm·(Ld − Lq) = iq²
MTPA 直线（SPMSM）： id = 0
等转矩线：           iq = T / (1.5·Pp·(ψm + (Ld − Lq)·id))
电流极限圆：         id² + iq² = imax²
电压极限椭圆：       (Vdc/√3)² = (id·Rs − ωe·Lq·iq)² + (iq·Rs + ωe·Ld·id + ωe·ψm)²
```

- 电机在电压约束内运行时：解 MTPA 线与等转矩线的交点
- 电机超出电压约束时：解电压约束曲线与等转矩线的交点

在 *ω* 与 *T* 的网格上算出 *id*、*iq* 表后，模块用插值求范围内任意 (*ω*, *T*) 输入的
*idref* 与 *iqref*；超出表格边界则截断（clip）。

**2. `Non-linear model with Ld, Lq, and FluxPM LUTs`（非线性 Ld/Lq/磁链查表）**

与集中参数法思路相同，但每次计算 *id*、*iq* 时都刷新 *Ld(id,iq)*、*Lq(id,iq)*、*FluxPM(id,iq)* 的值。
模块迭代这些计算直到 *id*、*iq* 收敛。

**3. `Non-linear model with D,Q-flux linkage LUTs`（非线性 d/q 磁链查表）**

同上，但每次刷新的是 *ψd(id,iq)*、*ψq(id,iq)*，同样迭代到收敛。

**4. `Non-linear model with id and iq LUTs`（直接用 id/iq 参考电流表）**

用于手动提供 *id(T,ω)*、*iq(T,ω)* 表，通常来自仿真或台架测试。

也可用 Motor Control Blockset™ 的 `mcb.generateMotorLUT` 函数生成这些表。

> **勘误说明**：本条「电压极限椭圆」官方英文站原文显示为 `(VDC/3)² = ...`，
> 中文站显示为 `(VDC·√3)² = ...`。对照 `mtpacontrolreference` 的 `vmax = vdc/√3`，
> 正确形式应为 **(Vdc/√3)² = ...**（即 Vdc²/3）。本存档按后者呈现。

### Vdc 输入方式与技术路线

| 电机参数输入方式 | Vdc 输入方式 | 技术路线 |
|---|---|---|
| Linear lumped | Specify via dialog | 用固定 Vdc 算 2D id/iq 表，插值求参考电流 |
| Linear lumped | Input port – 3D LUT（电压分片） | 算含电压分片的 3D 表，按端口 Vdc 取片 |
| Linear lumped | Input port – 2D LUT（ω 缩放） | 固定 Vdc 算 2D 表，端口 Vdc 变化时按转速 ω 缩放 |
| Non-linear DQ-flux / Ldq-FluxPM / id-iq LUTs | Specify via dialog | 对应查表 + 固定 Vdc 求参考电流 |
| 同上 | Input port – 3D LUT | 3D 查表按电压分片 |
| 同上 | Input port – 2D LUT | 2D 查表按 ω 缩放 |

此外，用 **Vdc input method** 可配置模块通过参数 **DC voltage to compute LUTs (V)** 接受固定母线电压，
或通过独立输入端口 **Vdc** 接受可变母线电压。

关于 Motor Control Blockset 对 PMSM 使用的完整方程与假设，见《PMSM 的数学模型》。

---

## 示例

- **PMSM Drive Characteristics and Constraint Curves** —— 用特性绘图与里程碑转速函数获得控制轨迹
- **Field-Weakening Control (with MTPA) of Nonlinear PMSM Using Lookup Table** —— 非线性 PMSM 查表弱磁

---

## 端口

| 端口 | 方向 | 说明 |
|---|---|---|
| **Tref** | 输入 | 参考转矩（Nm） |
| **⍵m** | 输入 | 机械转速（rad/s） |
| **Vdc** | 输入 | 可变母线电压（V）。Vdc 输入方式选 Input port 时启用 |
| **Idref** | 输出 | 参考 d 轴电流（A） |
| **Iqref** | 输出 | 参考 q 轴电流（A） |

数据类型：全部 `single` | `double` | `fixed point`

---

## 参数

### 电机参数

| 参数 | 默认 | 说明 |
|---|---|---|
| **Motor topology** | `Interior PMSM` | PMSM 类型（内置式 / 表贴式） |
| **Field weakening control method** | `CVCP` | 弱磁方法：`CVCP` / `CCCP` / `VCLMT` / `NONE`。前三种仅 SPMSM 可选；IPMSM 走 VCLMT |
| **Number of pole pairs** | `4` | 极对数 |
| **Stator resistance per phase, Rs (Ohm)** | `0.36` | 定子相电阻 |
| **Vdc input method** | `Specify via dialog` | 见上文技术路线表 |
| **DC voltage to compute LUTs (V)** | `24` | 母线电压（对话框指定时） |
| **DC bus voltage breakpoint vector, Vdc (V)** | `[18,30]` | 3D 表的电压断点向量 |
| **Motor parameter input method** | `Linear model with lumped parameters` | 见上文四种方式 |
| **Enable percentages for torque breakpoint vector** | `off` | 用百分比定义转矩断点 |
| **Enable custom breakpoint vectors for torque and speed** | `off` | 自定义转矩/转速查找向量 |
| **Reference percentage torque breakpoint vector, Trefpct (%)** | `[0,50,100]` | 百分比转矩断点 |
| **Torque envelope for speed breakpoint vector, wrpm (rpm)** | `[0.3 0.3 0.15 0.05]` | 转速断点的转矩包络 |
| **Reference torque breakpoint vector, Tref (Nm)** | `[0,0.15,0.3]` | 转矩断点（Nm） |
| **Mechanical speed breakpoint vector, wrpm (rpm)** | `[0,1000,2000,6000]` | 转速断点（rpm） |
| **Current Limit, I_limit (A)** | `7.1` | 最大相电流限值 |
| **Viscous damping coefficient, Bv (Nm-s/rad)** | `2.636875217824e-6` | 黏性阻尼系数 |

### 非线性查表参数（按输入方式启用）

| 参数 | 说明 |
|---|---|
| **D-axis current breakpoint vector, id (A)** | `[-40,-20,0,20]`，Ld/Lq/FluxPM 表的 d 轴电流向量 |
| **Q-axis current breakpoint vector, iq (A)** | `[-40,-20,0,20,40]`，同上 q 轴 |
| **Use measured (instead of computed) torque** | `off`，提供实测转矩查表数据 |
| **Measured torque LUT, T(id,iq) (Nm)** | 实测转矩表 |
| **Stator d-axis inductance, Ld (H)** | 线性方式时的 Ld |
| **Stator q-axis inductance, Lq (H)** | 线性方式时的 Lq |
| **Permanent magnet flux linkage (Wb)** | 线性方式时的 λpm |
| **D-axis flux linkage LUT, FluxD (id,iq) (Wb)** | DQ 磁链方式 |
| **Q-axis flux linkage LUT, FluxQ (id,iq) (Wb)** | DQ 磁链方式 |
| **Ld LUT / Lq LUT / PM flux linkage LUT (id,iq)** | Ld/Lq/FluxPM 方式 |
| **Reference id/iq LUT, id(Tref,wrpm[,Vdc]) (A)** | id/iq 方式：2D 表 *id(T,ω)* 或 3D 表 *id(T,ω,Vdc)* |

### 输入单位

| 参数 | 默认 | 说明 |
|---|---|---|
| **Input units** | `Per-Unit (PU)` | 块输入单位制 |
| **Base voltage (V)** | `24/sqrt(3)` | 标幺基准电压 |
| **Base current (A)** | `19.3` | 标幺基准电流 |
| **Base speed (rpm)** | `4107` | 标幺基准转速 |
| **Base torque (Nm)** | `0.74112` | 标幺基准转矩（内部计算，不可改） |
| **Allow scaled-down motor parameters with CodeGen** | `on` | 定点生成时按标幺缩放内部参数以提高精度；关闭则内部转 SI 再转回，便于运行期改表 |

### 绘图选项

启用条件：参数输入方式为 Linear lumped / DQ-flux / Ldq-FluxPM，且 Vdc 为 Specify via dialog。

- **Enable saving the computed LUTs** —— 保存模块算出的表
- **Compute (and plot) id and iq LUTs**（按钮）—— 计算并绘制 id/iq 表
- **Use default options for plotting** / **Motor speed (RPM)** / **Motor torque (Nm)**
- **Enable plotting the drive characteristics** / **Include the drive characteristics for an increased motor current**
- **Plot constraint curves**（按钮）—— 画约束曲线
- **Compute and show**（按钮）—— 计算并显示额定转矩、额定转速、最高转速

详见《Plot Constraint Curves and Drive Characteristics for PMSM and SynRM Directly from Block Parameters
Dialog Box》。

---

## 扩展能力

- **C/C++ 代码生成** —— 用 Simulink® Coder™ 生成 C/C++ 代码
- **定点转换** —— 用 Fixed-Point Designer™ 设计与仿真定点系统

## 版本历史记录

在 R2022b 中推出

## 另请参阅

- **模块：** PMSM FeedForward Control | PMSM Torque Estimator | LUT based SynRM Control Reference |
  LUT based ACIM Control Reference
- **函数：** `mcb.generateMotorLUT`

---

## 对 e11 的意义

> 以下为项目批注，非官方原文。

⭐ **这是与 e11 方案最匹配的模块。** 四条路线对应 e11 的演进：

| e11 阶段 | 参数输入方式 | 数据来源 |
|---|---|---|
| 快速验证 | Linear lumped | 额定点 Ld/Lq/λpm 单值 |
| **主方案** | Non-linear with Ld, Lq, FluxPM LUTs | ECE 导出的 Ld(id,iq)/Lq(id,iq)/FluxPM(id,iq) 表 |
| 备选 | Non-linear with D,Q-flux LUTs | ECE 的 λd/λq 磁链表（更接近原始数据） |
| 已建好参考表 | Non-linear with id and iq LUTs | `mcbGenerateTables` / `mcb.generateMotorLUT` 生成的 id(T,ω)/iq(T,ω) |

💡 建表流程（见 `16-fwc-mtpa-nonlinear-pmsm-lut.md` 第 7、12 步）：

```
CSV → mcbGenerateTables(pmsm, inverter, 'jmagindfiles2inddq', seed)
    → mcbGenerateTables(pmsm, inverter, 'idiqLUTs', seed)
    → 灌进本模块的 LUT 参数
```

⚠️ e11 的 MAT 数据要先按 `Lq = λq/iq`、`Ld = (λd − λpm)/id` 反推出干净电感表再导出。
