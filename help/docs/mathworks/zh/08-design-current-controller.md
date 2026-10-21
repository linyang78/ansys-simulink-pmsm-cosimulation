# 设计电流控制器子系统

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/ug/design-current-controller.html`
> （**该页无官方中文翻译，中文站正文同为英文**；以下为整理者翻译）
> 存档：2026-10-21 · R2026b · 英文版：`en/08-design-current-controller.md`
> 定位：「设计磁场定向控制算法」五步工作流的第 2 步。

---

## 设计步骤

**第 1 步**　在 Simulink 库浏览器的 Motor Control Blockset™ 库中，用 **PI Controller** 模块
（Controls/Controllers 库）设计 *d* 轴与 *q* 轴电流控制。（图中为 *d* 轴电流控制器子系统。）

MATLAB® 函数 `mcb.getPIControllerParameters`（在模型初始化脚本中）计算
*d* 轴、*q* 轴电流控制器与转速控制器的 PI 增益。
增益计算方法见《估计控制增益并调节控制参数》。
示例：初始化脚本 `mcb_pmsm_foc_qep_f28379d_data.m` 使用的采样时间 *Ts* = `50` μs。

子系统图中的 *Enable* 变量是用于复位控制器的 Data Store Memory，加不加可选。

子系统还用三个常量模块，取值分别为：

- `PI_params.Kp_i`
- `Ki_i*Ts`
- `0`

用同样方法搭 *q* 轴电流 PI 控制器，然后把 *d* / *q* 两个 PI 子系统集成为一个
Current_Controllers 子系统。

**第 2 步**　从 `Motor Control Blockset/Controls/Math Transforms` 库把
**Clarke Transform**、**Park Transform**、**Inverse Park Transform**、**PWM Reference Generator**
模块加入第 1 步建好的 Current_Controllers 子系统。

**第 3 步**　把第 2 步的组件集成为一个子系统（Closed Loop Control，实现闭环磁场定向控制）。

**第 4 步**　建一个 **Output Scaling** 子系统缩放 PWM 输出，
输出归一化占空比（`0`–`1`）给被控对象模型。

**第 5 步**　把电流换算（Calculate Phase Currents）、QEP 位置解码（Calculate Position and Speed）、
闭环控制、输出缩放四个子系统集成一个新子系统；
加入 **Trigger** 模块并把 **Trigger type** 设为 `function-call`。

**第 6 步**　在该子系统中加入 **Function-Call Generator** 模块，
其 **Sample time** 设为控制环采样时间 *Ts*（默认 `50e-6` s）。

**第 7 步**　把被控对象模型与第 6 步的控制器子系统接起来。
被控对象模型的搭建步骤见《使用 Motor Control Blockset 创建被控对象模型》。

> [原页面此处有 7 张子系统结构图：antiwindup / all_transforms / closedloop / outputscaling /
> withtrigger / integrate1 / integrate2，存档从略]

---

## 要点提炼

- **两个 PI**：*d* 轴、*q* 轴各一个 PI 控制器，输入为参考电流与实测 d-q 电流之差，输出为 d-q 参考电压
- **四个变换**：Clarke（ia,ib→αβ）、Park（αβ→dq）、Inverse Park（dq→αβ）、PWM Reference Generator（→占空比）
- **触发执行**：Trigger + Function-Call Generator 固定控制环执行周期（示例 50 μs，即 20 kHz 电流环）
- **抗饱和**：图中可见 anti-windup 结构；MCB 的 PI Controller 模块有积分限幅（PIConfig）
- **Enable 复位**：开环切闭环或故障时用 Enable 复位 PI 积分器

---

## 另请参阅

- 上一步：Design Current and Position Scaling Subsystems
- 下一步：Current Controller Manual Gains
- 总纲：`07-design-field-oriented-control-algorithm.md`
- 等效成品模块：`09-field-oriented-current-controller.md`（把上述 1–3 步封装成一个模块）

---

## 对 e11 的含义

> 以下为项目批注，非官方原文。

💡 第 6 步的 Function-Call Generator 对应 e11 控制模型的「电流环 20 kHz」调度。

💡 第 5 步的 Calculate Position and Speed 对应 QEP 解码——
如果 e11 最终用无传感器（Flux Observer / Sliding Mode Observer），
这一步要换成观测器输出，其余结构不变。

⚠️ 例程默认 50 μs 电流环周期与 TI 样板一致；e11 若用 F28379D 可直接沿用，
但实际载波频率仍须按功率级方案确定（见设计文档 §8 未决项）。
