# Field-Oriented Current Controller（模块）

> **MathWorks 官方文档存档（中文）**
> 来源：`https://www.mathworks.com/help/mcb/ref/fieldorientedcurrentcontroller.html`
> （官方无中文翻译；以下为整理者翻译）
> 存档：2026-10-21 · R2026b · Since R2023b · 英文版：`en/09-field-oriented-current-controller.md`
> 库：Motor Control Blockset / Control / Induction Machine / Controllers
> 　　Motor Control Blockset / Control / Synchronous Machine / Controllers

---

## 描述

用磁场定向控制（FOC）技术实现三相电机的电流控制。

该模块用 FOC 算法实现三相 PMSM 或 ACIM 的电流控制。
输入：*d* / *q* 轴参考电流、实测 a、b 相电流、电机电角度、PI 控制器参数；
输出：驱动电机的三相电压。

模块内部用 Clarke 与 Park 变换从实测相电流和电角度算出实际 *d* / *q* 电流，
用 PI Controller 模块搭 *d* / *q* 轴电流控制器，
由参考与实际电流之差生成参考电压驱动电机。
关于模块实现的 FOC 算法细节，见《Field-Oriented Control》。

模块支持 SI 与标幺两种输入，**但所有输入端单位必须一致**。

> 💡 这是 `08-design-current-controller.md` 第 1–3 步（两个 PI + 三种变换）的**成品封装**。
> 内部结构一样，直接拖模块即可，不必自己搭变换。

---

## 示例

| 示例 | 内容 |
|---|---|
| Swap Motors with Single Model Deployment of Sensor-Based FOC Algorithm | 工业驱动中用传感器 FOC 运行 PMSM，实时换电机不重部署（铭牌参数自适应） |
| Swap Motors with Single Deployment of Sensorless FOC Algorithm | 同上但无传感器（Flux Observer 估位置） |
| Generate Motor Control Models for Selected Algorithm and Hardware | 按选定算法与硬件生成 Simulink® 模型 |

---

## 端口

### 输入

| 端口 | 类型 | 说明 |
|---|---|---|
| **IdqRef** | 向量 | 参考 *d* / *q* 轴电流 `IdqRef = [IdRef, IqRef]` |
| **IabMeas** | 向量 | 实测 a、b 相电流 `IabMeas = [IaMeas, IbMeas]` |
| **θe** | 标量 | 电机电角度（单位由参数定） |
| **VSatLim** | 标量 | d-q 参考电压的饱和限。取决于母线电压与 PWM 方式：SPWM 取 `Vdc/2`，SVM 取 `Vdc/√3` |
| **Kp,Ki·Ts** | 向量 | *d* / *q* 轴 PI 增益与采样时间复用：`[Kp(d), Ki·Ts(d), Kp(q), Ki·Ts(q)]` |
| **PIConfig** | 向量 | PI 积分器初值与限幅：`[上限, 下限, d轴积分初值, q轴积分初值]` |
| **Enable** | 标量 | `1` 使能输出；`0` 复位内部 PI（注意：Vabc 可能保持之前算出的值） |

数据类型：全部支持 `single` | `double` | `fixed point`

### 输出

| 端口 | 类型 | 说明 |
|---|---|---|
| **Vabc** | 向量 | 驱动电机的三相电压 |
| **Debug** | 向量 | 调试复用信号：*Idq*（实测 d/q 电流）、*Vdq*（PI 输出电压）、*Vαβ*（反 Park 电压）、*Iαβ*（Clarke 电流） |

💡 **Debug 端口是联调利器**：联合仿真时把 *Idq*、*Vdq* 接出来，
和 ECE 组件给出的 d/q 电流对比，立刻能看出是变换约定问题还是观测器问题
（Park 变换系数约定见 `04-simscape-pmsm-block.md` 的警示）。

---

## 参数

| 参数 | 取值 | 说明 |
|---|---|---|
| **Input electrical position unit** | `Radians`（默认）\| `Degrees` \| `Per-unit` | 电角度输入单位 |
| **Number of data points for sine-cosine lookup table** | `1024`（默认，范围 [125, 4095]） | 内部 sin/cos 查表规模（定点实现省算力） |
| **Alpha (phase-a) axis alignment** | `D-axis`（默认）\| `Q-axis` | α 轴与 d 轴还是 q 轴对齐 |
| **Saturation method** | `D-Q equivalence`（默认）\| `Prioritize D axis` \| `Prioritize Q axis` | 电压饱和时的处理策略 |
| **PWM method** | `SVM`（默认）\| `SPWM` | 决定 VSatLim 的基准 |

### 饱和方法详解

- **`D-Q equivalence`**：vd 与 vq 同比缩放，保持矢量方向不变。
  这是标准做法，弱磁区行为可预期。
- **`Prioritize D axis`**：优先保 d 轴（保磁链 / 弱磁电流），牺牲 q 轴。
- **`Prioritize Q axis`**：优先保 q 轴（保转矩），牺牲 d 轴。

---

## 扩展能力

- **C/C++ 代码生成** —— 用 Simulink® Coder™ 生成 C/C++ 代码
- **定点转换** —— 用 Fixed-Point Designer™ 设计与仿真定点系统

## 版本历史记录

在 R2023b 中推出

## 另请参阅

PWM Reference Generator | PI Controller | Park Transform | Inverse Park Transform | Clarke Transform |
Sine-Cosine Lookup

**主题**
- Open-Loop and Closed-Loop Motor Control Techniques
- Field-Oriented Control

---

## 对 e11 的含义

> 以下为项目批注，非官方原文。

⚠️ 弱磁段电压饱和频繁，`Saturation method` 选错会表现为「高速掉转矩」。
e11 若出此现象，先查这里是不是被设成了 `Prioritize Q axis`。

💡 `VSatLim` 端口对 e11 应取 `Vdc/√3 = 230.94 V`（SVM），与设计文档 §3.1.1 的基速计算口径一致。
