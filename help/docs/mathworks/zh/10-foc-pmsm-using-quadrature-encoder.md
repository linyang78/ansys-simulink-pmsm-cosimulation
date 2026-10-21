# 使用正交编码器的 PMSM 磁场定向控制

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gs/foc-pmsm-using-quadrature-encoder.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/10-foc-pmsm-using-quadrature-encoder.md`
> 说明：这是 Motor Control Blockset 的**标杆 FOC 示例**
> （带编码器、转速外环 + 电流内环、可部署到 TI C2000 硬件）。

---

## 概述

此示例采用磁场定向控制（FOC）方法控制三相永磁同步电机（PMSM）的转速。
FOC 算法需要转子位置反馈，该反馈通过正交编码器获得。关于 FOC 的细节，见《磁场定向控制》。

正交编码器由一个圆盘组成，盘上有两条相差 90 电角度的轨道（通道）。
由此产生相位差 90 度的两个脉冲（A 和 B）以及一个索引脉冲（I）。
控制器根据 A、B 通道之间的相位关系与通道状态的转换来确定电机的旋转方向。

---

## 模型

| 模型 | 硬件 |
|---|---|
| `mcb_pmsm_foc_qep_f28069m` | F28069M 控制卡 + DRV8312-69M-KIT 逆变器 |
| `mcb_pmsm_foc_qep_f28069LaunchPad` | LAUNCHXL-F28069M + BOOSTXL-DRV8305 |
| `mcb_pmsm_foc_system` | 系统级仿真模型（LaunchPad 配置） |
| `mcb_pmsm_foc_qep_f28379d` | LAUNCHXL-F28379D + BOOSTXL-DRV8305 / BOOSTXL-3PHGANINV |

这些模型可用于仿真与代码生成。

---

## 必需的 MathWorks 产品

**仿真：**

| 模型 | 产品 |
|---|---|
| `mcb_pmsm_foc_qep_f28069m` / `..._f28069LaunchPad` / `mcb_pmsm_foc_system` | Motor Control Blockset™ + Fixed-Point Designer™ |
| `mcb_pmsm_foc_qep_f28379d` | Motor Control Blockset |

**生成代码并部署：**

| 模型 | 产品 |
|---|---|
| 上述 F28069M 三个模型 | Motor Control Blockset + Embedded Coder® + C2000™ Microcontroller Blockset + Fixed-Point Designer™ |
| `mcb_pmsm_foc_qep_f28379d` | Motor Control Blockset + Embedded Coder® + C2000™ Microcontroller Blockset + Fixed-Point Designer™（仅优化代码生成时需要） |

---

## 前提条件

1. 获取电机参数。Simulink® 模型自带默认参数，可用数据手册或其他来源的值替换。

   如果有电机控制硬件，可用 Motor Control Blockset 参数估计工具估计参数
   （见《使用 Motor Control Blockset 参数估计工具估计电机参数》）。
   该工具会用估计值更新 MATLAB® 工作区的 *motorParam* 变量。

2. 如果参数来自数据手册或其他来源，需在与模型关联的初始化脚本中更新电机参数与逆变器参数
   （见《估计控制增益并调节控制参数》）。

   如果用了参数估计工具，可以更新逆变器参数，但**不要再改脚本里的电机参数**——
   脚本会自动从更新后的 *motorParam* 工作区变量中提取。

---

## 仿真模型

1. 打开示例附带的一个模型
2. 点**仿真**选项卡的**运行**
3. 点**数据检查器**查看分析结果

---

## 生成代码并在目标硬件上运行

此示例使用主机模型与目标模型。主机模型是控制器硬件板的用户界面，可在主机上运行。
使用主机模型的前提是先把目标模型部署到控制器板。
主机模型通过串行通信向目标模型发指令，以闭环方式运行电机。

**必需的硬件：**

- F28069M 控制卡 + DRV8312-69M-KIT 逆变器：`mcb_pmsm_foc_qep_f28069m`
- LAUNCHXL-F28069M 控制器 + BOOSTXL-DRV8305 逆变器：`mcb_pmsm_foc_qep_f28069LaunchPad` 与
  `mcb_pmsm_foc_system`
- LAUNCHXL-F28379D 控制器 +（BOOSTXL-DRV8305 或 BOOSTXL-3PHGANINV）逆变器：`mcb_pmsm_foc_qep_f28379d`

> **注意：** 使用 BOOSTXL-3PHGANINV 逆变器时，确保其底层与 LAUNCHXL 板之间有适当绝缘。

**步骤：**

1. 仿真目标模型并观测结果
2. 完成硬件连接
3. 模型自动计算 ADC（电流）偏移值。要禁用（默认启用），把初始化脚本里的
   `inverter.ADCOffsetCalibEnable` 设为 0。也可手动计算并写入脚本
   （见《以开环控制方式运行三相 AC 电机并校准 ADC 偏移量》）
4. 计算正交编码器索引偏移值并写入目标模型初始化脚本
   （见《PMSM 的正交编码器偏移量校准》）
5. 验证编码器刻线数：检查并更新初始化脚本里的 `pmsm.QEPSlits`
   （对应 Quadrature Decoder 的 **Encoder slits** 参数）
6. 按所需硬件配置打开目标模型（默认配置的修改见《模型配置参数》）
7. 给 LAUNCHXL-F28379D 的 CPU2 加载示例程序（如 `c28379D_cpu2_blink.slx`，用 GPIO31 点灯），
   确保 CPU2 没有错误配置成占用预留给 CPU1 的板载外设
8. 点**硬件**选项卡的**编译、部署和启动**部署目标模型
9. 点目标模型里的 `mcb_host_model_f28069m.slx` 超链接打开主机模型
10. 用变量 `target.comport` 指定通信端口
11. 更新主机模型里的 Reference Speed 值
12. 点**仿真**选项卡的**运行**运行主机模型
13. 把 Start / Stop Motor 开关切到 On 开始运行电机
14. 在主机模型的 Time Scope 里观测 RX 子系统的调试信号

> **注意：** 用 F28379D 控制器时，还可以选择要监控的调试信号。

---

## 与其他文档的关系

- FOC 原理 → `01-field-oriented-control.md`
- 五步工作流 → `07-design-field-oriented-control-algorithm.md` + `08-design-current-controller.md`
- 被控对象 → `05-creating-plant-model.md`
- 参数 → `13-estimate-pmsm-parameters.md`
- 增益 → `15-estimate-control-gains-and-tune.md`、`14-gain-calculation-and-tuning.md`
- 开环启动 / ADC / 编码器校准见本页第 3、4 步

---

## 对 e11 的意义

> 以下为项目批注，非官方原文。

💡 `mcb_pmsm_foc_qep_f28379d` 是 e11 控制模型的**最近参照**：
转速外环 + d/q 电流内环、QEP 位置、标幺制、50 μs 电流环。差异点：

① e11 用非线性查表（`17-lut-based-pmsm-control-reference.md`），示例用 MTPA Control Reference；
② e11 电机数据来自 ECE（Twin Builder），示例用线性参数。

联调时先用本示例跑通「MCB 全链」，再逐块替换成 e11 的查表和 ECE 对象，**问题定位会快很多**。
