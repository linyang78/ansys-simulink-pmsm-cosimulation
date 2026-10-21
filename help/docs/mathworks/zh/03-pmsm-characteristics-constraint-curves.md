# PMSM 驱动特性与约束曲线

> **MathWorks 官方文档存档（中文）**
> 来源：`https://ww2.mathworks.cn/help/mcb/ug/pmsm-characteristics-constraint-curves.html`（返回 403，正文取自英文站）
> 存档：2026-10-21 · R2026b · 英文版：`en/03-pmsm-characteristics-constraint-curves.md`
> 说明：官方正文逐段整理，代码块为官方 Live Script 示例代码。

---

## 概述

此示例使用 Motor Control Blockset™，演示如何用 PMSM 特性绘图函数与 PMSM 里程碑转速识别函数来获得控制轨迹。

**必需的 MathWorks 产品：** Motor Control Blockset, Simulink

---

## PMSM 类型与 d-q 轴

永磁同步电机按永磁体安装位置分两类：

- 磁钢贴在转子表面的，叫**表贴式 PMSM（SPMSM）**
- 磁钢埋在转子内部的，叫**内置式 PMSM（IPMSM）**

在 d-q 转子参考系中，**d 轴**平行于转子磁场方向，**q 轴**与之垂直并超前 d 轴。
SPMSM 的 d、q 轴电感相等；**IPMSM 的 q 轴电感大于 d 轴电感**。
这使得 IPMSM 除永磁转矩外还能利用磁阻转矩。

---

## 转折转速与基速

**转折转速**：在给定电流限制下，转矩-转速（驱动特性）曲线的形状发生拐点的那个转速。
当用额定转矩（额定电流）绘制驱动特性时，转折转速也称为**额定转速**或**基速**。

---

## 三条约束曲线

画约束曲线是为了理解可能的运行区域与边界：

- **MTPA 轨迹**：在允许的定子电流下给出最大转矩。
- **MTPV 轨迹**：在满足定子电压约束的前提下给出最大转矩。
- **电压极限曲线**（IPMSM 为椭圆、SPMSM 为圆）：以**特征电流**点为中心，
  该曲线**随转子转速升高而收缩**。

---

## 三个运行段

### 第 I 段（恒转矩区）

电机从零转矩升到额定转矩，工作点沿 MTPA 轨迹从 O 移到 A（线段 OA），对应 MTPA 尖端的 id、iq。
当电压极限椭圆同时与 MTPA 曲线和电流极限圆相切时，对应转速 ω1 即额定转速，是第一个里程碑转速。

### 第 II 段（弱磁区，电流受限）

到达 A 点时电流已达上限，弱磁策略启动。电流轨迹沿电流极限圆从 A 移到 B（线段 AB），期间保持电流约束。
B 点是电压椭圆同时与电流极限圆和 MTPV 曲线相切的转速，是第二个里程碑转速。

### 第 III 段（MTPV 区）

B 点之后椭圆继续收缩，沿 MTPV 轨迹给出最优转矩，直到 C 点（线段 BC）达到最高转速。
无摩擦的理想电机在 MTPV 下理论最高转速为无穷大；实际受摩擦限制。
Motor Control Blockset 中「含摩擦的最高转速」定义为摩擦力矩与电机转矩平衡时的转速。

计算出的最高转速是**第三个里程碑转速**。某些电机配置下 MTPV 不可达，此时摩擦限制了 B 点，
不存在 C 点，这类电机只有**两个里程碑转速**。

---

## 里程碑转速计算

用 `mcb.PMSMSpeeds` 函数获取全部里程碑转速。不同弱磁控制策略对应的可运行转速不同。
默认弱磁方法是电压电流受限最大转矩（**VCLMT**）控制，也叫最优电流矢量控制。函数返回 **rpm**。

```matlab
inverter.V_dc = 24;
pmsm = mcb.getPMSMParameters('BLY171D');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter);
disp(milestone_speeds);
%   5393
%   9373
```

提高额定电流后可以得到第三段（MTPV）：

```matlab
pmsm.I_rated = 8;   % 假设更高的额定电流以获得 MTPV 轨迹
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter);
disp(milestone_speeds);
%   2342
%   2958
%   24369
```

### 不同弱磁方法的对比

| FWCMethod | 里程碑转速 (rpm) | 说明 |
|---|---|---|
| `vclmt` | 5393 / 9373 | 默认，最优电流矢量控制 |
| `cvcp` | 5393 / 7008 / 8361 | 恒压恒功率 |
| `cccp` | 5393 / 7008 | 恒流恒功率 |
| `none` | 5393 / 6226 | id 恒为 0，不做弱磁 |

```matlab
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'vclmt');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'cvcp');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'cccp');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'none');
```

### 各里程碑点的 id / iq / 转速

输出数组每列对应一个里程碑转速，每行分别是 **id、iq、转速（电角速度 rad/s）**。

```matlab
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter, 'FWCMethod', 'vclmt', 'outputAll', 0);
[outputArray] = mcb.PMSMSpeeds(pmsm, inverter, 'FWCMethod', 'vclmt', 'outputAll', 1);
disp(outputArray);
%  1.0e+03 *
%       0      -0.0018
%   0.0018      0.0004
%   2.2591      3.9262
```

---

## 绘制驱动特性

驱动特性显示给定运行约束下的转矩-转速、功率-转速、电流-转速曲线。
用 `mcb.PMSMCharacteristics` 函数绘制。

把 `driveCharacteristics` 设为 2 时，函数会额外画一张 vd-vq 空间的图，含电压约束曲线与电压轨迹。

```matlab
inverter = mcb.getInverterParameters('BoostXL-DRV8305');
pmsm = mcb.getPMSMParameters('BLY171D');
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 2, 'constraintCurves', 1, 'FWCMethod', 'vclmt')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'cvcp')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'cccp')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'none')
```

### 按 Imax 绘制

电机持续承载恒定负载转矩时即额定工况，对应电流为额定电流。电机的短期定额高于连续电流定额。

```matlab
mcb.PMSMCharacteristics(pmsm, inverter, "FWCMethod", "vclmt", "driveCharacteristics", 1, "imax", 8, "constraintCurves", 0)
```

---

## 自定义驱动特性

`pmsm` 结构需要 `p`、`Rs`、`Ld`、`Lq`、`FluxPM`、`B`、`I_rated` 字段；
`inverter` 结构需要 `V_dc` 字段。

```matlab
inverter.V_dc = 24;
pmsm.p = 4;
pmsm.Rs = 0.45;
pmsm.Ld = 1e-3;
pmsm.Lq = pmsm.Ld * 1.4;
pmsm.FluxPM = 5.2e-3;
pmsm.B = 1.16e-5;
pmsm.I_rated = 2;
w_rpm = 7000;
T_load = 0.01;
FWCMethod = "vclmt";
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', w_rpm, 'torque', T_load, ...
    'FWCMethod', FWCMethod, 'constraintCurves', 0, 'driveCharacteristics', 1);
```

---

## 在 id-iq 平面画约束曲线

```matlab
inverter = mcb.getInverterParameters('BoostXL-DRV8305');
pmsm = mcb.getPMSMParameters('BLY171D');
pmsm.Rs = 0.1;
pmsm.Lq = pmsm.Ld * 1.8;
w_rpm = 5000;
T_load = 0;
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', w_rpm, 'torque', T_load);
```

### 在最高转速处

约束曲线可用于二次校验算出的转速是否正确。在最高转速处，图中三条曲线相交：
电流极限圆、电压极限曲线、等转矩曲线。

```matlab
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter);
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', milestone_speeds(end), torque = 0)
```

### 在里程碑转速处

除最高转速处的相交外，注意在转折转速处 MTPA 曲线、电流极限圆、电压约束曲线三者相交。

```matlab
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter, 'constraintCurves', 1);
disp(milestone_speeds);
%   5645
%   9641
```

### 多转速叠画

用 `opacity` 选项设置当前所画约束曲线的透明度：

- `opacity` = 1（默认）：新建图窗
- `opacity` < 1（大于 0）：用不同透明度叠加画电压约束、MTPA、MTPV 曲线

```matlab
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 4000, 'torque', 0, 'opacity', 1)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 5000, 'opacity', 0.8)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 6000, 'opacity', 0.7)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 7000, 'opacity', 0.6)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 8000, 'opacity', 0.5)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 9000, 'opacity', 0.4)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 10000, 'opacity', 0.3)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 11000, 'opacity', 0.2)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', 12000, 'opacity', 0.1)
```

---

## 实际电压方程 vs 近似方程

通常 PMSM 的 vd、vq 方程含 i×r 项，计算时会被忽略，因为高速时该项可忽略。
本例可在计算最高转速时选择是否包含 i×r 项。实际方程为：

```
vd = id·r − ω·Lq·Iq
vq = iq·r + ω·Ld·id + ω·ψm
```

```matlab
max_speed_actual_eqn = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', verbose, 'voltageEquation', 'actual');
max_speed_approx_eqn = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', verbose, 'voltageEquation', 'approximate');
disp([max_speed_actual_eqn max_speed_approx_eqn])
%   5393  5359
%   9373  8775
```

对比可见：最高转速处实际方程算出 9373 rpm，近似方程只有 8775 rpm，**差约 6.8%**。
高速段忽略 i×r 会带来可观误差。

---

## 案例：IPMSM 与 SPMSM

本节的案例演示如何为 IPMSM 与 SPMSM 找到可行的控制轨迹。工作流程：

1. 在**转折转速**处画驱动特性（含 MTPV）与约束曲线
2. 在 **MTPV 起始转速**处，用 `driveCharacteristics`=0、`opacity`=0.5 叠加约束曲线
3. 在**最高转速**处，用 `driveCharacteristics`=0、`opacity`=0.3 叠加约束曲线

当电阻足够大时，MTPV 曲线会随转速动态漂移，电流轨迹不沿任何一条单 MTPV 曲线。
图中的青色曲线是**可达 MTPV 曲线**——因为它用实际方程动态求解工作点。

```matlab
% IPMSM 案例
inverter.V_dc = 24;
pmsm.p = 4;
pmsm.Rs = 0.45;
pmsm.Ld = 1e-3;
pmsm.Lq = 1.25 * pmsm.Ld;
pmsm.FluxPM = 5.2e-3;
pmsm.I_rated = 10;
pmsm.B = 1.16e-5;
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter);
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', milestone_speeds(1), 'driveCharacteristics', 1, 'constraintCurves', 1)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', milestone_speeds(2), 'driveCharacteristics', 0, 'constraintCurves', 1, 'opacity', 0.5)
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', milestone_speeds(end), 'driveCharacteristics', 0, 'constraintCurves', 1, 'opacity', 0.3)

% SPMSM 案例（Lq = Ld）
pmsm.Lq = pmsm.Ld;
```

---

## 另请参阅

- PMSM Constraint Curves and Their Application
- SynRM Constraint Curves and Their Application
- Field-Weakening Control (with MTPA) of Nonlinear PMSM Using Lookup Table

## 参考文献

[1] Mihailovic, Zoran. "Modeling and Control Design of Vsi-Fed Pmsm Drive Systems With Active Load."
Thesis, Virginia Tech, 1998.

[2] Li, Muyang. "Flux-Weakening Control for Permanent-Magnet Synchronous Motors Based on Z-Source
Inverters." Thesis, 2014.

---

## 对 e11 的落地建议

> 以下为项目批注，非官方原文。

把 e11 的实测值填进 `pmsm` 结构体，就能直接画出 e11 的约束曲线：

```matlab
inverter.V_dc = 400;
pmsm.p = 4;
pmsm.Rs = 0.01338;
pmsm.Ld = 2.26e-4;      % 饱和后约 1.61e-4
pmsm.Lq = 2.97e-4;      % 轻载约 6.65e-4
pmsm.FluxPM = 0.075883;
pmsm.I_rated = 433;
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 2, 'constraintCurves', 1, 'FWCMethod', 'vclmt')
```

注意：e11 是**饱和电机**，上述单一电感值只能给出粗略曲线。
要精确，应用 `LUT based PMSM Control Reference`（见 `17-lut-based-pmsm-control-reference.md`）。
