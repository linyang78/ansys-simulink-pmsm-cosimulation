# 标幺制（Per-Unit System）

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/gs/per-unit-system.html`（正文取自英文站）
> 存档：2026-10-21 · R2026b · 英文版：`en/06-per-unit-system.md`
> 说明：官方正文逐段整理。

---

## Motor Control Blockset 使用的 SI 单位

| 物理量 | 单位 | 符号 |
|---|---|---|
| 电压 | 伏特 | V |
| 电流 | 安培 | A |
| 转速 | 弧度/秒、转/分 | rad/s、rpm |
| 转矩 | 牛·米 | N·m |
| 功率 | 瓦特 | W |

**说明**：转速的 SI 单位是 rad/s，但多数厂商用 rpm。MCB 偏好 rpm，也可按需选用任一种。

---

## 标幺制

标幺制（PU）在电气工程中常用，用来表示电压、电流、功率等物理量的值，
在电力系统分析的变压器与交流电机里广泛使用。
嵌入式工程师也用它来做代码优化与可扩展性设计，尤其是定点目标。

对给定物理量，标幺制用量值相对**基准值**的比例来表示：

```
标幺值 = SI 值 / 基准值
SI 值 = 标幺值 × 基准值
```

通常取系统的额定值作为基准值；有时也取最大可测量值。
选定基准值后，所有信号都以该基准值的标幺形式表示。

例：若电流基准值取 10 A，则 2 A 表示为 (2/10) PU = 0.2 PU。

---

## MCB 的基准值约定

### 基准电压

基准电压 = 逆变器能提供的最大相电压。

- **空间矢量 PWM（SVPWM）**：`PU_System.V_base = inverter.V_dc / sqrt(3)`
- **正弦 PWM（SPWM）**：`PU_System.V_base = inverter.V_dc / 2`
- **断续 PWM（DPWM）**：`PU_System.V_base = inverter.V_dc / sqrt(3)`

⚠️ **这一点对本项目很关键**：e11 用 SVPWM，所以 `V_base = 400/√3 = 230.94 V`。
早期设计文档里写成 `Vdc/√3 × √2`（多乘了 √2），是错的。
SVPWM 线性区相电压**峰值**就是 `Vdc/√3`，不需要再乘 √2。

### 基准电流

基准电流 = 逆变器电流采样电路能测的最大电流，一般取逆变器的 `ISenseMax`。

```matlab
PU_System.I_base = inverter.ISenseMax
```

⚠️ 这个值必须由**逆变器的电流采样量程**决定，不能用电机峰值电流随意替代。

### 基准转速

基准转速 = 电机额定转速，也就是在额定电压、额定负载下**不弱磁**能达到的最高转速。

这与设计文档 §3.1.1 算出的 e11 满载基速 ≈ 4040 rpm 是同一个概念。

### 基准转矩

基准转矩由基准电流数学推导得出，**物理上电机不一定真能输出这个转矩**。

```matlab
PU_System.T_base = (3/2) × pmsm.p × pmsm.FluxPM × PU_System.I_base
```

💡 注意这个公式里**没有磁场饱和修正**。
对 e11：`1.5 × 4 × 0.075883 × 433 = 197.1 N·m`，
而实测 MTPA 最大转矩是 246.4 N·m——说明基准转矩不等于实际最大转矩。

### 基准功率

```matlab
PU_System.P_base = (3/2) × PU_System.V_base × PU_System.I_base
```

其中：

- `Vdc`：提供给逆变器的直流电压
- `Imax`：接在逆变器电流传感器上的 ADC 能测的最大电流
- `p`：PMSM 极对数
- `FluxPM`：PMSM 的永磁磁链
- `pmsm`、`inverter`、`PU_System`：MATLAB 工作区里保存相应变量的结构体

### 峰值与有效值

电压与电流一般取额定正弦量的**峰值**作为 1PU。
因此基准值是有效值乘 √2，即相-中性点之间的峰值。

---

## 为什么用标幺制

- 提高代码执行的计算效率，因此是定点目标的首选
- 产生可扩展的控制算法，可跨多套系统复用

---

## 把 SI 单位模型转成标幺制（FOC 示例）

### 先在 SI 单位下准备并仿真

运行脚本 `FOCofPMSMData` 把参数载入基础工作区。
脚本里 `ControllerVariant` 设为 `SI`，即控制子系统用 SI 单位版本。

```matlab
FOCofPMSMData;

mdl = "FOCofPMSM";
open_system(mdl);
sim(mdl);
Simulink.sdi.view;
```

### 计算基准值并切到标幺

```matlab
PU_System = mcb.getPUSystemParameters(pmsm, inverter);
ControllerVariant = 'PU';
```

### 模型里需要转换的关键位置

- 参考转速：经 `convert2PU` 转标幺
- 电流反馈：经 `Convert2PU` 转标幺
- 位置反馈：经 `ConvertTheta2PU` 转标幺
- **Mechanical to Electrical Position**：机械角单位改 *Per unit*
- **Speed Measurement**：位置与转速单位改标幺
- **Field-Oriented Current Controller**：电位置输入单位改标幺
- **PI 控制器**：限幅改为 -1 ~ +1
- **Convert2Voltages**：把 Vabc 输出还原成实际电压送给电机对象
- **SpeedController**：限幅改为 `±pmsm.I_rated/PU_System.I_base`
- **FOC Default Controller Gains**：输出单位改标幺

```matlab
hilite_system('FOCofPMSM/Control/Per Unit Control/Speed Controller/convert2PU');
hilite_system('FOCofPMSM/Control/Per Unit Control/Current Controller/Convert2PU');
hilite_system('FOCofPMSM/Control/Per Unit Control/Current Controller/ConvertTheta2PU');
hilite_system('FOCofPMSM/Control/Per Unit Control/Current Controller/Mechanical to Electrical Position');
hilite_system('FOCofPMSM/Control/Per Unit Control/Current Controller/Speed Measurement');
```

### 在标幺下再仿真

```matlab
sim(mdl);
Simulink.sdi.view;
```

对比 SI 与标幺两种表示的曲线可见：**控制器响应完全相同**——
标幺制不改变物理行为，只改变数值表示。

---

## 另请参阅

**主题**

- Per-Unit System of Units (Simscape Electrical)

---

## 对 e11 的取值表

> 以下为项目批注，非官方原文。

| 基准量 | 公式 | e11 取值 |
|---|---|---|
| `V_base` | `Vdc/√3`（SVPWM） | **230.94 V**（Vdc = 400 V） |
| `I_base` | 逆变器 `ISenseMax` | 待定（需由功率级方案给出） |
| `N_base` | 满载基速 | **约 4040 rpm** |
| `T_base` | `1.5·p·λpm·I_base` | `1.5×4×0.075883×433 = 197.1 N·m` |
| `P_base` | `1.5·V_base·I_base` | `1.5×230.94×433 ≈ 150.0 kW` |
