# PMSM 的弱磁控制（使用 MTPA）

> **官方原文存档** —— 来源 `https://www.mathworks.com/help/mcb/gs/field-weakening-control-mtpa-pmsm.html?lang=zh_CN`
> 存档日期：2026-10-21 · 版本标注 R2026b · 英文版见 `field-weakening-control-mtpa-pmsm.en.md`
> 说明：本文件为官方中文页面正文的**逐段照录**。本地已复制的示例文件见 `help/matlab-examples/field-weakening-mtpa/`。

---

此示例使用: C2000 Microcontroller Blockset、Embedded Coder、Motor Control Blockset、Simulink Coder、Simulink

此示例采用磁场定向控制 (FOC) 方法来控制三相永磁同步电机 (PMSM) 的转矩和转速。FOC 算法需要转子位置反馈，该反馈通过正交编码器获得。有关 FOC 的详细信息，请参阅磁场定向控制。

## 弱磁控制

当您使用 FOC 算法让电机以额定磁通运行时，最大转速受定子电压、额定电流和反电动势的限制。此转速称为基转速。若超出此转速，机器的运行就会变得复杂，因为反电动势大于供电电压。但是，如果您将 d 轴定子电流 (Id) 设置为负值，则转子磁链会减小，从而使电机以高于基转速的转速运行。这种操作称为电机的弱磁控制。

根据机器的连接负载和额定电流，弱磁控制中的 d 轴参考电流 (Id) 也会限制 q 轴参考电流 (Iq)，从而限制转矩输出。因此，电机在达到基转速之前一直在恒定转矩区域内运行。如上图所示，它以高于基转速的转速，在有限的转矩下，在恒定功率区域内运行。

参考电流的计算取决于电机和逆变器参数。

> **注意：**
>
> - 对于某些表贴式 PMSM，在额定电流下可能无法实现更高的转速，具体情况视参数而定。为了实现更高的转速，您需要用高于额定电流的最大电流使电机重载（如果机器的热条件在允许范围内）。
> - 当电机以高于基转速的转速运行时，我们建议您监控电机的温度。在电机运行期间，如果电机温度升高，超出制造商建议的温度，出于安全原因，请关闭电机。
> - 当电机以高于基转速的转速运行时，我们建议您以小步长增大转速参考值，以避免弱磁所带来的动态变化，这可能会使某些系统不稳定。

## 最大转矩电流比 (MTPA)

对于内置式 PMSM，转子磁路中的凸极导致 Lq/Ld 比率较高（大于 1）。这会在转子中产生磁阻转矩（除了现有电磁转矩之外）。有关详细信息，请参阅 MTPA Control Reference。

因此，您可以按 Id 和 Iq 的最佳组合操作机器，并在相同的定子电流 Im 下获得更高的转矩。

这会提高机器的效率，因为此时定子电流损失最小。用于生成参考电流 Id 和 Iq 以在机器中产生最大转矩的算法称为最大转矩电流比 (MTPA)。

对于内置式 PMSM (IPMSM)，在达到基转速之前，此示例使用 MTPA 方法计算参考电流 Id 和 Iq。对于表贴式 PMSM (SPMSM)，在达到基转速之前，该示例通过使用零 d 轴参考电流实现 MTPA 运行。

为了使电机以高于基转速的转速运行，此示例根据电机类型计算 MTPA 和弱磁控制的参考电流 Id 和 Iq。对于表贴式 PMSM，使用恒压恒功率 (CVCP) 控制方法。对于内置式 PMSM，使用电压和电流限制最大转矩 (VCLMT) 控制方法。

有关 MTPA Control Reference 模块的信息，请参阅 MTPA Control Reference。

## 目标通信

对于硬件实现，此示例使用主机模型和目标模型。主机模型运行在主机上，与部署在连接到电机的硬件上的目标模型进行通信。主机模型使用串行通信对目标模型发出指令，并以闭环控制方式运行电机。

弱磁控制和 MTPA 都需要生成遵循以下各项限制的参考电流：

- 电流限制圆
- 电压限制椭圆
- 电机温度

要确定遵循这些限制的工作点，请参阅由函数 `mcb.PMSMCharacteristics` 生成的绘图。

在弱磁区域中，某些 PMSM 可能需要高于电机额定电流的定子电流。有关详细信息，请参阅由函数 `mcb.PMSMCharacteristics` 生成的绘图。

## 模型

此示例对以下硬件配置使用了多个模型：

**带弱磁和 MTPA 的 PMSM 的转速控制：**

- `mcb_pmsm_fwc_qep_f28069LaunchPad`
- `mcb_pmsm_fwc_qep_f28379d`

**带弱磁和 MTPA 的内置式 PMSM (IPMSM) 的转速控制：**

- `mcb_ipmsm_fwc_qep_f28379d`

> **注意：** 此模型使用在模型初始化脚本中定义的 ADLEE-BM-180E IPMSM 参数。ADLEE-BM-180E IPMSM 的凸极率约为 10%（Lq 大约比 Ld 高 10%）。鉴于凸极率较低，这种电机需要更高的 Id 电流，才能进入弱磁区域并以高于额定转速的转速运行。然而，该电机的额定电流只有 9A。因此，当您在弱磁区域运行此电机时，较低的凸极率会使电机快速吸收高 Id 电流（并快速达到额定电流限值），但只能在基转速的基础之上获得有限的转速增加。通过凸极率较高的 IPMSM，您可以使用此模型实现高于基转速的更高转速。

**带 MTPA 的 PMSM 的转矩控制：**

- `mcb_pmsm_mtpa_qep_f28069LaunchPad`
- `mcb_pmsm_mtpa_qep_f28379d`

您可以将这些模型用于仿真和代码生成。

## 必需的 MathWorks 产品

**要对模型进行仿真，您需要：**

1. 对于模型 `mcb_pmsm_fwc_qep_f28069LaunchPad` 和 `mcb_pmsm_mtpa_qep_f28069LaunchPad`：
   - Motor Control Blockset™
   - Fixed-Point Designer™
2. 对于模型 `mcb_pmsm_fwc_qep_f28379d`、`mcb_ipmsm_fwc_qep_f28379d` 和 `mcb_pmsm_mtpa_qep_f28379d`：
   - Motor Control Blockset™

**要生成代码并部署模型，您需要：**

1. 对于模型 `mcb_pmsm_fwc_qep_f28069LaunchPad` 和 `mcb_pmsm_mtpa_qep_f28069LaunchPad`：
   - Motor Control Blockset™
   - Embedded Coder®
   - C2000™ Microcontroller Blockset
   - Fixed-Point Designer™
2. 对于模型 `mcb_pmsm_fwc_qep_f28379d`、`mcb_ipmsm_fwc_qep_f28379d` 和 `mcb_pmsm_mtpa_qep_f28379d`：
   - Motor Control Blockset™
   - Embedded Coder®
   - C2000™ Microcontroller Blockset
   - Fixed-Point Designer™（仅在优化代码生成时需要）

## 前提条件

1. 获取电机参数。我们对 Simulink® 模型提供了默认电机参数，您可以用电机数据表或其他来源的值替换这些默认值。
   不过，如果您有电机控制硬件，则可以通过使用 Motor Control Blockset 参数估计工具来估计要使用的电机的参数。有关说明，请参阅使用 Motor Control Blockset 参数估计工具估计电机参数。
   参数估计工具使用估计的电机参数更新 `motorParam` 变量（在 MATLAB® 工作区中）。
2. 如果您从数据表或其他来源获得电机参数，请在与 Simulink® 模型相关联的模型初始化脚本中更新电机、逆变器和位置传感器校准参数。有关说明，请参阅估计控制增益并调节控制参数。
   如果您使用参数估计工具，则可以在模型初始化脚本中更新逆变器和位置传感器校准参数，但不能更新电机参数。该脚本会自动从更新后的 `motorParam` 工作区变量中提取电机参数。

## 仿真（转速控制和转矩控制）模型

此示例支持仿真。请按照以下步骤仿真模型。

1. 打开此示例附带的一个模型。
2. 点击**仿真**选项卡上的**运行**来仿真该模型。
3. 点击**仿真**选项卡上的**数据检查器**来查看和分析仿真结果。

### 分析转速控制模型的仿真结果

该模型使用标幺制来表示转速、电流、电压、转矩和功率。在工作区中键入 `PU_System`，可查看将这些量的一个标幺值转换为国际单位的结果。

观测转速和电流控制器的系统动态特性。另请注意电机以高于基转速的转速运行时的负 Id 电流。

> **注意：** 在开始时，该示例以开环控制方式运行电机。在检测到正交编码器的索引脉冲后，电机开始以闭环控制方式运行。启动算法大约需要 0.5 秒来执行此转换。忽略在此初始阶段观测到的转速和位置反馈信号的任何瞬变。

### 分析转矩控制模型的仿真结果

使用由以下三种方法生成的 Id 和 Iq 参考电流运行仿真：

1. 使用 MTPA Control Reference 模块生成参考电流。
2. 使用 Vector Control Reference 模块手动生成 MTPA 参考电流。
3. 在不使用 MTPA 的情况下生成控制参考电流。

第一种方法在假定线性电感的情况下运用数学计算来确定参考电流 Id 和 Iq。

第二种方法可用来为具有非线性电感的电机手动生成 MTPA 查找表。您可以用通过在 +(π/2) 到 -(π/2) 之间扫描转矩角生成的 Id 和 Iq 参考值来说明此方法。

使用最后一种方法，无需 MTPA 算法即可获得参考电流。

您可以在数据检查器中比较由这三种方法生成的转矩和功率。

在前面的示例中，您可能注意到，使用 MTPA 生成的电转矩是 0.34PU，而在不使用 MTPA 的情况下生成的电转矩是 0.27PU。您可能还注意到，随着转矩角的变化，产生的最大转矩与使用 MTPA 产生的转矩匹配。d 轴电流为负表明 MTPA 利用了内置式 PMSM 的磁阻转矩。

> **注意：** 如果使用的是表贴式 PMSM，请在以下位置处的 MTPA Control Reference 模块中，将电机参数的类型从**内置式 PMSM** 改为**表贴式 PMSM**：
>
> - `mcb_pmsm_fwc_qep_f28069LaunchPad/Speed Control`
> - `mcb_pmsm_fwc_qep_f28379d/Speed Control`
> - `mcb_pmsm_mtpa_qep_f28069LaunchPad/Torque Control/MTPA_Reference`
> - `mcb_pmsm_mtpa_qep_f28379d/Torque Control/MTPA_Reference`

## 生成代码并将模型部署到目标硬件

本节将指导您生成代码并在目标硬件上运行 FOC 算法。

此示例使用一个主机模型和一个目标模型。主机模型是控制器硬件板的一个用户界面。您可以在主机上运行主机模型。使用主机模型的前提条件是将目标模型部署到控制器硬件板上。主机模型使用串行通信对目标 Simulink® 模型发出指令，并以闭环控制方式运行电机。

### 必需的硬件

此示例支持以下硬件配置。您还可以在 MATLAB® 命令提示符下使用目标模型名称打开对应硬件配置的模型。

- LAUNCHXL-F28069M 控制器 + BOOSTXL-DRV8305 逆变器：`mcb_pmsm_fwc_qep_f28069LaunchPad` 和 `mcb_pmsm_mtpa_qep_f28069LaunchPad`
- LAUNCHXL-F28379D 控制器 + BOOSTXL-DRV8305 逆变器：`mcb_pmsm_fwc_qep_f28379d`、`mcb_ipmsm_fwc_qep_f28379d` 和 `mcb_pmsm_mtpa_qep_f28379d`

有关与前述硬件配置相关的连接，请参阅 LAUNCHXL-F28069M 和 LAUNCHXL-F28379D 配置。

### 运行模型，以通过弱磁和 MTPA 实现转速和转矩控制

1. 按照上一节操作来仿真模型并分析仿真结果。
2. 完成硬件连接。
3. 转矩控制模型需要带 QEP 传感器的内置式 PMSM，由带转速控制的外部测功机（使用转速控制模型）驱动。
4. 该模型自动计算 ADC（或电流）偏移值。要禁用此功能（默认启用），请在模型初始化脚本中将值 0 更新为变量 `inverter.ADCOffsetCalibEnable`。
   您也可以计算 ADC 偏移值，并在模型初始化脚本中手动更新它。有关说明，请参阅以开环控制方式运行三相 AC 电机并校准 ADC 偏移量。
5. 计算正交编码器索引偏移值，并在与目标模型相关联的模型初始化脚本中更新它。有关说明，请参阅 PMSM 的正交编码器偏移量校准。
6. 按所需的硬件配置打开目标模型。如果您要更改目标模型的默认硬件配置设置，请参阅模型配置参数。
7. 将一个示例程序加载到 LAUNCHXL-F28379D 的 CPU2（例如使用 GPIO31 操作 CPU2 蓝色 LED 的程序 `c28379D_cpu2_blink.slx`），以确保 CPU2 没有错误地配置为使用预留给 CPU1 的板载外设。有关示例程序或模型的详细信息，请参阅 Texas Instruments 入门指南 C2000 Microcontroller Blockset (C2000 Microcontroller Blockset) 中的"任务 2 - 为 TI Delfino F28379D LaunchPad（双核）创建、配置和运行模型"部分。
8. 点击**硬件**选项卡上的**编译、部署和启动**以将目标模型部署到硬件上。
9. 点击目标模型中的 `mcb_pmsm_fwc_host_model.slx` 主机模型超链接以打开关联的主机模型。
   有关主机模型和目标模型之间串行通信的详细信息，请参阅 Host-Target Communication。
10. 在与目标模型关联的模型初始化脚本中，使用变量 `target.comport` 指定通信端口。该示例使用此变量来更新主机模型中可用的 Host Serial Setup、Host Serial Receive 和 Host Serial Transmit 模块的端口参数。
11. 在转速控制模型中，更新 Reference Speed (RPM) 模块值。在转矩控制模型中，使用 Imag Reference 模块更新当前请求。
12. 点击**仿真**选项卡上的**运行**以运行主机模型。
13. 将 Start / Stop Motor 开关的位置切换到 On 以开始运行电机。
14. 在主机模型的 Time Scope 内，输入不同参考转速（或电流）并观测来自 RX 子系统的调试信号。

> **注意：**
>
> - 如果位置偏移量不正确，此示例可能会导致电机电流过大。为了避免这种情况，请确保正确计算了位置偏移量，并在工作区变量 `pmsm.PositionOffset` 中更新了它。
> - 当电机以高于基转速的转速运行时，我们建议您监控电机的温度。在电机运行期间，如果电机温度升高，超出制造商建议的温度，出于安全原因，请关闭电机。
> - 当电机以高于基转速的转速运行时，我们建议您以小步长增大转速参考值，以避免弱磁所带来的动态变化，这可能会使某些系统不稳定。

## 参考资料

[1] B. Bose, Modern Power Electronics and AC Drives. Prentice Hall, 2001. ISBN-0-13-016743-6.

[2] Lorenz, Robert D., Thomas Lipo, and Donald W. Novotny. "Motion control with induction motors." Proceedings of the IEEE, Vol. 82, Issue 8, August 1994, pp. 1215-1240.

[3] Morimoto, Shigeo, Masayuka Sanada, and Yoji Takeda. "Wide-speed operation of interior permanent magnet synchronous motors with high-performance current regulator." IEEE Transactions on Industry Applications, Vol. 30, Issue 4, July/August 1994, pp. 920-926.

[4] Li, Muyang. "Flux-Weakening Control for Permanent-Magnet Synchronous Motors Based on Z-Source Inverters." Master's Thesis, Marquette University, e-Publications@Marquette, Fall 2014.

[5] Briz, Fernando, Michael W. Degner, and Robert D. Lorenz. "Analysis and design of current regulators using complex vectors." IEEE Transactions on Industry Applications, Vol. 36, Issue 3, May/June 2000, pp. 817-825.

[6] Briz, Fernando, et al. "Current and flux regulation in field-weakening operation [of induction motors]." IEEE Transactions on Industry Applications, Vol. 37, Issue 1, Jan/Feb 2001, pp. 42-50.

[7] TI Application Note, "Sensorless-FOC With Flux-Weakening and MTPA for IPMSM Motor Drives."

## 另请参阅

- Field-Weakening Control (with MTPA) of Nonlinear PMSM Using Lookup Table
- PMSM Drive Characteristics and Constraint Curves
