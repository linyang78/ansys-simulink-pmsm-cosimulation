# 使用 Motor Control Blockset 创建被控对象模型

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/ug/creating-plant-model.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/05-creating-plant-model.md`
> 说明：官方正文逐段整理，代码块/路径为官方原文。

---

## 概述

精确的被控对象模型是电机控制系统开发的重要组成部分。
创建精确的被控对象模型后，你可以验证控制系统功能、执行闭环模型在环测试、
用仿真调节控制器增益，并在部署到实际被控对象之前优化算法。

使用 Motor Control Blockset™ 创建被控对象模型时，需要建模下列组件：

- 永磁同步电机（PMSM）
- 平均值逆变器
- 传感器与信号调理电路
- 处理器外设：模数转换器（ADC）与脉冲宽度调制器（PWM）

可通过以下方式验证所创建对象模型的功能：

1. 从控制算法读取归一化 PWM 占空比
2. 仿真连接负载的电机
3. 从仿真获得输出相电流（按 ADC 计数）与输出位置（按编码器脉冲计数）

---

## 工作流六步

创建被控对象模型的工作流包含以下步骤。

> **注意**：请参阅示例《使用正交编码器的 PMSM 磁场定向控制》中使用的 `mcb_pmsm_foc_qep_f28379d.slx`
> 模型内的被控对象模型。

| 步 | 主题 | 路径 |
|---|---|---|
| 1 | 使用 PMSM 模块和电机参数设计被控对象模型 | `ug/use-pmsm-estimated-parameters-design-model.html` |
| 2 | 添加 Average-Value Inverter 模块 | `ug/add-average-inverter-modeling.html` |
| 3 | 创建电机相电流检测与信号调理子系统 | `ug/create-motor-phase-current-sensing-algorithm.html` |
| 4 | 创建位置感测子系统 | `ug/create-positioning-sensing-subsystem.html` |
| 5 | 在被控对象模型中添加延迟 | `ug/add-delay-plantmoodeling.html` |
| 6 | 集成模块和子系统 | `ug/integrate-blocks-and-subsystems-plantmodeling.html` |

---

## 另请参阅

- Estimate PMSM Parameters Using Parameter Estimation Blocks
- Design Field-Oriented Control Algorithm
- Field-Oriented Control of PMSM Using Quadrature Encoder

---

## 六步要点

> 以下为整理者批注，非官方原文。

| 步 | 做什么 | 关键模块 |
|---|---|---|
| 1 | 用估计出的电机参数配置电机本体模型 | Interior PMSM / Surface Mount PMSM / PMSM (Simscape) |
| 2 | 逆变器平均值模型 | Average Value Inverter |
| 3 | 电流采样 + 运放调理 + ADC 量化 | 信号调理子系统 |
| 4 | 位置采样与计数 | QEP 脉冲计数输出 |
| 5 | 加计算/采样延迟 | Transport Delay 等 |
| 6 | 把控制器与对象接成闭环 | Trigger + Function-Call Generator |

### 对 e11 的含义

💡 e11 的高保真模型在 Twin Builder（ECE 组件），比 MCB 的平均值对象精度高。
纯 Simulink 路线可用 `04-simscape-pmsm-block.md` 里讲的 `PMSM (Tabulated Ld, Lq and PM)` 模块搭对照对象，
再按本文六步补上逆变器、采样、延迟——**MCB 的增益整定和 Autotuner 可以直接在这个对象上跑**，不必等台架。
两条路线（Twin Builder 高保真 / Simulink 快速）互为交叉验证。

⚠️ 第 5 步「加延迟」最容易被忽略：MCB 的整定结果对采样延迟和计算延迟敏感
（见 `15-estimate-control-gains-and-tune.md`）。对象模型里不加延迟，整出来的增益到硬件上会偏。
