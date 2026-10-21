# 估计控制增益并调节控制参数

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gs/estimate-control-gains-from-motor-parameters.html`
> 存档：2026-10-21 · R2026b · 英文版：`en/15-estimate-control-gains-and-tune.md`
> 说明：这是《增益计算与整定》引用的完整示例页。

---

## 概述

调节作为磁场定向控制（FOC）算法一部分的转速与转矩控制环。
可从下列方法中选择，用电机、逆变器与控制器可用的系统或模块传递函数计算控制环增益：

- 使用 Field Oriented Control Autotuner 模块
- 使用 FOC Default Controller Gains 模块
- 使用 Simulink® Control Design™
- 使用模型初始化脚本

每种方法都需要下列控制参数：

- 电机、逆变器与目标参数
- 控制执行时间
- 延迟与标幺制数值

---

## 四种方法

### 1. Field-Oriented Control Autotuner 模块

Motor Control Blockset™ 的 FOC Autotuner 模块能实时自动调节 FOC 应用中的 PID 控制环。
可自动调节与下列环路关联的 PID 控制器：

- 直轴（*d* 轴）电流环
- 交轴（*q* 轴）电流环
- 转速环

对每个被调节的环路，模块以**闭环方式**执行整定试验，**不使用该环路的参数化模型**。
可以指定模块调节各控制环的顺序；整定某一环路时，模块不影响其他环路。

### 2. FOC Default Controller Gains 模块

该模块把控制增益计算集成进控制器代码。
用它可以**在运行期**确定控制器增益，切换不同电机设置时无需重新编译。

### 3. Simulink Control Design

可设计与分析在 Simulink 中建模的控制系统，自动调节任意 SISO / MIMO 控制架构（含 PID）。
可把 PID 自动整定部署到嵌入式软件，实时计算 PID 增益。

还能求工作点、计算不同工况下 Simulink 模型的精确线性化，
并在不修改模型的前提下计算基于仿真的频率响应。

### 4. 模型初始化脚本

可用 Motor Control Blockset 示例附带的初始化脚本，初始化估计控制增益所需的控制参数。

以带正交编码器的 PMSM 为例：

1. 打开使用初始化脚本的示例：

   ```matlab
   openExample('mcb/FOCQepExample')
   ```

2. 在 MATLAB® 中打开该示例的初始化脚本（`.m`）。查找关联脚本名的方法：
   1. 打开示例模型，选 **建模 > 模型设置 > 模型属性**
   2. 在**回调**选项卡的 **InitFcn** 字段里，就是 Simulink 在模型编译开始时执行的脚本名

3. 用**工作区**编辑控制变量。例如改定子电阻 `Rs`，就修改 `pmsm` 结构体的 `Rs` 字段

---

## 初始化控制参数的函数

与目标模型关联的初始化脚本会调用下列函数，并用必要的变量设置工作区。

| 函数 | 说明 |
|---|---|
| `mcb.getPMSMParameters` | 输入电机品牌/型号（如 BLY171D），返回 `pmsm` 结构体；计算永磁磁链与额定转矩；若工作区有参数估计得到的 `motorParam` 会自动装载 |
| `mcb.getACIMParameters` | ACIM 版本（如 EM_Synergy） |
| `mcb.getInverterParameters` | 输入逆变器品牌/型号（如 BoostXL-DRV8305），返回 `inverter` 结构体并计算逆变器电阻 |
| `mcb.getProcessorParameters` | 输入处理器型号与 PWM 开关频率，返回 `target` 结构体并计算 ePWM 计数器周期 |
| `mcb.getPUSystemParameters` | 设置电压/电流/转速/转矩/功率的标幺基值，返回 `PU_System` |
| `mcb.getSISystemParameters` | SI 制基值，返回 `SI_System` |
| `mcb.updateInverterParameters` | 按所选硬件与电机更新逆变器参数 |

> **注意：** 对于预定义的处理器与驱动，初始化脚本使用默认值。

---

## 计算控制增益的函数

| 计算内容 | 函数 | 功能 |
|---|---|---|
| 电机基转速 | `mcb.getMotorBaseSpeed` | 额定电压与额定负载下 PMSM 的基转速（弱磁区外最高转速） |
| 电机特性 | `mcb.PMSMCharacteristics` | 转矩-转速、功率-转速、Idq-转速、最大相电流-转速特性 |
| ACIM 特性 | `mcb.ACIMCharacteristics` | 感应电机版本 |
| PI 增益（旧） | `mcb.getPIControllerParameters` | 计算 Id/Iq 电流环、转速环、**弱磁环**的 Kp/Ki |
| PI 增益（新，R2025a+） | `mcb.calcFOCGains` | 为 PMSM 计算 FOC PI 控制器增益与传递函数 |
| 频域分析 | `mcb.getMotorControlAnalysis` | 对算出的 PI 增益做频域分析（需 Control System Toolbox™） |

为 PMSM 计算 PI 控制器增益时，请改用 `mcb.calcFOCGains`。

---

## 另请参阅

- Field-Oriented Control of PMSM Using Quadrature Encoder
- Obtain Controller Gains to Run Motor Using Field-Oriented Control
- PMSM Constraint Curves and Their Application

---

## 对 e11 的意义

> 以下为项目批注，非官方原文。

💡 **选路建议**：

- 离线算增益 → 初始化脚本里调 `mcb.calcFOCGains`（R2025a+）或 `mcb.getPIControllerParameters`
- 上板后微调 → FOC Autotuner 模块（也能整定弱磁模式的磁链环）
- 电机即插即用 → FOC Default Controller Gains 模块（运行期算增益，不重编译）

⚠️ **非线性查表的影响**：`mcb.calcFOCGains` 按线性 Ld/Lq 建模。
e11 的 Ld/Lq 随电流变化，建议取**额定工作点附近**的电感值算增益，并在弱磁段用 Autotuner 复核。
