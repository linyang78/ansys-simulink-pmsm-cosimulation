# 使用参数估计模块估计 PMSM 参数

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gs/pmsm-parameter-estimation-using-recommended-hardware.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/13-estimate-pmsm-parameters.md`
> 说明：原页面较长，本存档保留全部章节与关键步骤。

---

## 概述

此示例使用 Motor Control Blockset™ 提供的参数估计模块，估计带正交编码器的 PMSM 的下列参数：

- 相电阻 *Rs*（欧姆）
- D 轴电感 *Ld*（亨）
- Q 轴电感 *Lq*（亨）
- 反电动势常数 *Ke*（Vpk_LL/krpm，Vpk_LL 为线电压峰值测量值）
- 电机惯量 *J*（kg·m²）
- 摩擦常数 *B*（N·m·s）

关于无传感器参数估计的示例，见《Generate Motor Control Models for Selected Algorithm and Hardware》。

电机参数估计对准确实现电机控制算法至关重要。
准确的电机参数使算法能精确计算控制参数，因此在用 FOC 等技术运行 PMSM 时，
准确的参数表示是获得精细转速与转矩控制的前提。
参数估计还能验证数据手册给出的值，并让你在 Simulink® 中准确复现被控对象模型，
从而仿真那些用实物硬件难以执行的场景与测试。

准确的仿真可反复重跑这些测试，用实物硬件则难以做到，
因此这些详尽的测试能轻松预测、发现并修复问题，包括难以复现的故障。

本示例演示如何用下列模块在 TI® 硬件板上设计与实现 PMSM 参数估计算法：

- PMSM Parameter Estimation Configurator
- PMSM Rs Estimator
- Ld Estimator
- Lq Estimator
- PMSM Mechanical Parameter Estimation

也可以本示例为参考，在不同硬件板或配置上用这些模块实现类似算法。

---

## 模型

目标模型在 `mcb_pmsm_param_est_f28379d/Parameter Estimation/Param Est` 子系统中使用参数估计模块。

子系统与对应模块：

| 子系统 | 用途 |
|---|---|
| `RsTest` | 用 Rs Estimator 模块估计电机电阻 |
| `LdTest` | 用 Ld Estimator 模块估计 *d* 轴电感 |
| `LqTest` | 用 Lq Estimator 模块估计 *q* 轴电感 |
| `MechParam` | 用 PMSM Mechanical Parameter Estimation 模块估计反电动势常数、惯量与摩擦常数 |

只做仿真时，目标模型直接显示估计值；部署到硬件时，用主机模型在硬件上估计。

**模型：** `mcb_pmsm_param_est_f28379d`

**必需的 MathWorks 产品：**

- 仿真：Motor Control Blockset（仅在修改示例模型时需要 Stateflow®）
- 代码生成与部署：Motor Control Blockset、Embedded Coder®、C2000™ Microcontroller Blockset、Stateflow

---

## 前提条件

检查并更新模型初始化脚本 `mcb_pmsm_param_est_f28379d_data.m` 中列出的强制性电机、逆变器及其他系统参数。

此外可以更新用于仿真的可选电机参数。

这些值可参考逆变器与电机硬件的数据手册确定。

---

## 仿真

1. 打开示例包含的目标模型
2. 如需修改参数估计配置，更新
   `mcb_pmsm_param_est_f28379d/Serial Receive/Variant Subsystem/Sim` 子系统中
   PMSM Parameter Estimation Configurator 模块的封装参数
3. 在**用户控制**中确保**参数估计**开关为**停止**
4. 点**仿真**选项卡的**运行**
5. 把**测试方法**设为**手动**或**自动**

**手动模式**：**测试方法**→**手动**；用**测试选择**按钮选第一个测试 `Rs`；
**参数估计**开关转**开始**，模型运行 *Rs* 估计并在**估计参数**字段显示计算值；
开关转**停止**；再选下一个测试重复。

**自动模式**：**测试方法**→**自动**；**参数估计**→**开始**，
模型按 `Rs` → `Ld` → `Lq` → `(Ke, J, B)` 的规定序列运行全部测试并显示参数值。

> **注意：** 必须按 `Rs` → `Ld` → `Lq` → `(Ke, J, B)` 的顺序运行，不要跳过任何测试。

仿真期间目标模型不支持 *J* 的计算。自动模式下**测试选择**按钮不起作用。

---

## 生成代码并部署

**必需的硬件：** LAUNCHXL-F28379D 控制器 + BOOSTXL-DRV8305 逆变器（`mcb_pmsm_param_est_f28379d`）

1. 完成硬件连接
2. 模型自动计算 ADC（电流）偏移值。要禁用（默认启用），把初始化脚本里
   `inverter.ADCOffsetCalibEnable` 设为 0。也可手动计算 ADC 偏移
   （见《以开环控制方式运行三相 AC 电机并校准 ADC 偏移量》）
3. 计算正交编码器索引偏移值并写入目标模型初始化脚本
   （见《PMSM 的正交编码器偏移量校准》）。验证编码器刻线数并更新 `pmsm.QEPSlits`
4. 打开目标模型（改硬件配置见《模型配置参数》）
5. 给 LAUNCHXL-F28379D 的 CPU2 加载示例程序（如 `c28379D_cpu2_blink.slx`），
   防止 CPU2 误占预留给 CPU1 的板载外设
6. 点**硬件**选项卡的**编译、部署和启动**
7. 确认目标模型变量在 MATLAB 基础工作区可用
8. 点主机模型超链接 `mcb_pmsm_param_est_host_f28379d.slx`（串行通信见 Host-Target Communication）
9. 需要时改主机模型里 PMSM Parameter Estimation Configurator 的封装参数
10. 用变量 `target.comport` 指定通信端口
11. **用户控制**里把**参数估计**开关设为**停止**
12. 点**运行**启动主机模型与目标硬件通信
13. **测试方法**选**手动**或**自动**；**活动测试**字段显示当前正在跑的测试
14. 用**调试信号**下拉框选信号，在示波器监视

### 保护性故障

模型可中断当前测试并点亮红色 LED 以保护硬件：

- **过电流故障**：从电源汲取的实际电流超过初始化脚本中 *motor.OverCurrLim* 与 *motor.I_rated* 指定的限值
- **欠压故障**：输入 DC 电压低于 *inverter.UnderVoltLim* 与 *inverter.V_dc* 指定的限值

**Error Code** 模块显示测试期间错误的诊断信息，
结合当前活动测试与对应参数估计模块的文档来定位根因。

测试完成后，主机模型把计算出的参数保存到基础工作区的 *motorParam* 变量中。

---

## 另请参阅

- **App：** Motor Hardware Configurator | Motor Parameter Estimator
- **模块：** PMSM Rs Estimator | Ld Estimator | Lq Estimator | PMSM Mechanical Parameter Estimator |
  PMSM Parameter Estimation Configurator
- **主题：** 使用自定义硬件估计 PMSM 参数 | 利用传感器反馈的 PMSM 运行时参数估计 |
  在实时系统上用参数估计模块估计 PMSM 参数 | 用基于 FPGA 的电机控制开发套件估计 PMSM 参数

---

## 对 e11 的意义

> 以下为项目批注，非官方原文。

💡 **估计顺序不能乱**：`Rs → Ld → Lq → (Ke, J, B)`。
*Ld* 估计要用到 *Rs*；机械参数估计（反电势常数 → 惯量 → 摩擦）要电机先能转起来。

💡 **e11 的特殊之处**：本工具估计的是**单点（线性化）参数**。
e11 的 *Ld* / *Lq* 随电流大幅变化（162–665 µH），所以：

- 用本工具拿 *Rs*、*Ke*、*J*、*B*（这些近似常数没问题）
- *Ld* / *Lq* 必须用 ECE 的 FEA 扫描数据建 (id, iq) 表，对应 `16-fwc-mtpa-nonlinear-pmsm-lut.md` 的查表方案
- MCB 也支持运行时按测点刷新，但非线性区的权威数据仍来自 FEA / 实测扫描

⚠️ **Ke 的定义**：这里是 `Vpk_LL/krpm`（线电压峰值 / 千转）。
换算到磁链时不要手工搬单位——用 `mcb.getPMSMParameters` 的结构体统一管理
（见 `04-simscape-pmsm-block.md` 的 ke/kt 换算）。
