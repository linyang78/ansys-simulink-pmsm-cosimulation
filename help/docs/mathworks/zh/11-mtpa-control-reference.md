# MTPA Control Reference（中文版）

> **官方原文存档** —— 来源 `https://www.mathworks.com/help/mcb/ref/mtpacontrolreference.html?lang=zh_CN`
> 存档日期：2026-10-21 · 版本标注 R2026b · 英文版见 `mtpacontrolreference.en.md`
> 说明：本文件为官方中文页面正文的**逐段照录**，公式按纯文本还原（原页面为图片/MathML，网页转文本时会散架）。
> 页面标题与模块名保持英文（官方即如此），正文为官方简体中文。

---

计算最大转矩电流比 (MTPA) 和弱磁运行的参考电流

**库:** Motor Control Blockset / Control / Synchronous Machine / Control Reference

## 描述

MTPA Control Reference 模块针对最大转矩电流比 (MTPA) 和弱磁运行计算 d 轴和 q 轴参考电流值。计算得到的参考电流值可为永磁同步电动机 (PMSM) 提供有效输出。

您可以指定参考转矩和反馈机械转速，该模块会输出 MTPA 和弱磁运行的对应 d 轴和 q 轴参考电流值。对于给定的机械转速，除了可能的最高转矩值，该模块还支持小于 PMSM 额定转矩的参考转矩值。

该模块通过求解数学关系来计算参考电流值。

此外，您还可以使用 **Vdc 输入方法**参数来配置该模块，以通过 **DC 电压(V)** 参数接受固定参考 DC 电压，或通过单独的输入端口 **Vdc** 接受可变参考 DC 电压。

这些方程描述模块对参考 d 轴和 q 轴电流值的计算：

### PMSM 的数学模型

下列模型方程描述转子磁通参考系中 PMSM 的动态特性：

```
vd = id·Rs + dλd/dt − ωe·Lq·iq

vq = iq·Rs + dλq/dt + ωe·Ld·id + ωe·λpm

λd = Ld·id + λpm

λq = Lq·iq

Te = (3/2)·p·(λpm·iq + (Ld − Lq)·id·iq)

Te − TL = J·dωm/dt + B·ωm
```

其中：

| 符号 | 含义 |
|---|---|
| vd | d 轴电压（伏特） |
| vq | q 轴电压（伏特） |
| id | d 轴电流（安培） |
| iq | q 轴电流（安培） |
| Rs | 定子相绕组电阻 (ohm) |
| λpm | 永磁磁链（韦伯） |
| λd | d 轴磁链（韦伯） |
| λq | q 轴磁链（韦伯） |
| ωe | 对应于定子电压频率的电角速度（弧度/秒） |
| ωm | 转子机械转速（弧度/秒） |
| Ld | d 轴绕组电感（亨） |
| Lq | q 轴绕组电感（亨） |
| Te | PMSM 产生的机电转矩 (Nm) |
| TL | 负载转矩 (Nm) |
| p | 电机极对数 |
| J | 惯量系数 (kg-m2) |
| B | 摩擦系数 (kg-m2/秒) |

### 基转速

基转速是在额定电压和额定负载下，弱磁区域之外的最大电机转速。下列方程描述电机基转速的计算。

逆变器电压约束通过计算 d 轴和 q 轴电压来定义：

```
vdo = −ωe·Lq·iq

vqo = ωe·(Ld·id + λpm)

vmax = vdc/√3 − Rs·imax ≥ sqrt(vdo² + vqo²)
```

电流极限圆定义电流约束，可以被视为：

```
imax² = id² + iq²
```

在以上方程中，对于表贴式 PMSM，`id` 为零。对于内置式 PMSM，该模块会考虑对应于 MTPA 的 `id` 和 `iq` 的值。

使用以下方程，我们可以将基转速计算为：

```
ωbase = (1/p) · vmax / sqrt( (Lq·iq)² + (Ld·id + λpm)² )
```

其中：

- ωe — 对应于定子电压频率的电角速度（弧度/秒）
- ωbase — 电机的机械基转速（弧度/秒）
- id — d 轴电流（安培）
- iq — q 轴电流（安培）
- vdo — 当 id 为零时的 d 轴电压（伏特）
- vqo — 当 iq 为零时的 q 轴电压（伏特）
- Ld — d 轴绕组电感（亨）
- Lq — q 轴绕组电感（亨）
- Rs — 定子相绕组电阻 (ohm)
- λpm — 永磁磁链（韦伯）
- vd — d 轴电压（伏特）
- vq — q 轴电压（伏特）
- vmax — 供给电机的相对于中性点电压（峰值）的基波最大值（伏特）
- vdc — 供给逆变器的 DC 电压（伏特）
- imax — 电机的最大相电流（峰值）（安培）
- p — 电机极对数

### 表贴式 PMSM

对于表贴式 PMSM，当电机低于基转速时，您可以通过使用零 d 轴电流来实现最大转矩。对于弱磁运行，该模块使用以下方程定义的恒压恒功率控制 (CVCP) 算法计算参考 d 轴电流：

**如果 ωm ≤ ωbase，则：**

```
id_mtpa = 0
iq_mtpa = Tref / ((3/2)·p·λpm)
id_sat  = id_mtpa = 0
iq_sat  = sat(iq_mtpa, imax)
```

**如果 ωm > ωbase，则：**

```
id_fw  = (ωe_base − ωe)·λpm / (ωe·Ld)
id_sat = max(id_fw, −imax)
iq_fw  = Tref / ((3/2)·p·λpm)
iq_lim = sqrt(imax² − id_sat²)
iq_sat = sat(iq_fw, iq_lim)
```

用于计算 `iq_sat` 的饱和函数为：

```
如果 iq_fw < −iq_lim，则：   iq_sat = −iq_lim
如果 iq_fw >  iq_lim，则：   iq_sat =  iq_lim
如果 −iq_lim ≤ iq_fw ≥ iq_lim，则：  iq_sat = iq_fw
```

该模块输出以下值：

```
Idref = id_sat
Iqref = iq_sat
```

其中：

- ωe — 对应于定子电压频率的电角速度（弧度/秒）
- ωm — 转子机械转速（弧度/秒）
- ωbase — 电机的机械基转速（弧度/秒）
- ωe_base — 电机的电气基转速（弧度/秒）
- id_mtpa — 对应于 MTPA 的 d 轴相电流（安培）
- iq_mtpa — 对应于 MTPA 的 q 轴相电流（安培）
- Tref — 参考转矩 (Nm)
- p — 电机极对数
- λpm — 永磁磁链（韦伯）
- id_fw — d 轴弱磁电流（安培）
- iq_fw — q 轴弱磁电流（安培）
- Ld — d 轴绕组电感（亨）
- imax — 电机的最大相电流（峰值）（安培）
- id_sat — d 轴饱和电流（安培）
- iq_sat — q 轴饱和电流（安培）
- Idref — 对应于参考转矩和参考转速的 d 轴电流（安培）
- Iqref — 对应于参考转矩和参考转速的 q 轴电流（安培）

### 内置式 PMSM

对于内置式 PMSM，您可以通过转矩方程计算 d 轴和 q 轴参考电流来实现最大转矩。对于弱磁运行，该模块使用电压和电流限制最大转矩 (VCLMT) 控制算法计算参考 d 轴电流。

MTPA 和弱磁运行的参考电流由以下方程定义：

```
im_ref = 2·Tref / (3·p·λpm)

im = min(im_ref, imax)

id_mtpa = λpm / (4·(Lq − Ld)) − sqrt( λpm² / (16·(Lq − Ld)²) + im²/2 )

iq_mtpa = sqrt( im² − (id_mtpa)² )

vdo = −ωe·Lq·iq
vqo = ωe·(Ld·id + λpm)

vdo² + vqo² = vmax²

(Lq·iq)² + (Ld·id + λpm)² ≤ (vmax/ωe)²

iq = sqrt( imax² − id² )

(Ld² − Lq²)·id² + 2·λpm·Ld·id + λpm² + Lq²·imax² − (vmax/ωe)² = 0
```

以下两个方程描述对应于给定转速值的最大可能转矩的弱磁电流的计算：

```
id_fw = −λpm/Ld + sqrt( (λpm/Ld)² − (Ld² − Lq²)·(λpm² + Lq²·imax² − (vmax/ωe)²) / (Ld² − Lq²) )

iq_fw = sqrt( imax² − id_fw² )
```

以下两个方程描述给定转速和转矩值下弱磁电流的计算。

```
9·p²·(Ld − Lq)²·Lq²·ωe²·iq_fw⁴
 + (9·p²·λpm²·Lq²·ωe² − 9·p²·(Ld − Lq)²·vmax²)·iq_fw²
 − 12·Tref·p·λpm·Ld·Lq·ωe²·iq_fw
 + 4·(Tref)²·Ld²·ωe² = 0

id_fw = −λpm/Ld + (1/Ld)·sqrt( (vmax/ωe)² − (Lq·iq_fw)² )
```

为了减少计算时间，该模块使用逼近来求解前面的多项式。

**如果 ωm ≤ ωbase，则：**

```
Idref = id_mtpa
Iqref = iq_mtpa
```

**如果 ωm > ωbase，则：**

```
Idref = max(id_fw, −imax)
iq_fw = sqrt( imax² − id_fw² )
如果 iq_fw < im，则：  Iqref = iq_fw
如果 iq_fw ≥ im，则：  Iqref = im
```

对于负参考转矩值，该模块会更新 `im` 和 `Iqref` 的符号，并相应地修改方程。

其中：

- im_ref — 产生参考转矩的估计最大电流（安培）
- im — 估计的最大电流的饱和值（安培）
- id_max — 最大 d 轴相电流（峰值）（安培）
- iq_max — 最大 q 轴相电流（峰值）（安培）
- Tref — 参考转矩 (Nm)
- Idref — 对应于参考转矩和参考转速的 d 轴电流分量（安培）
- Iqref — 对应于参考转矩和参考转速的 q 轴电流分量（安培）
- p — 电机极对数
- λpm — 永磁磁链（韦伯）
- id_mtpa — 对应于 MTPA 的 d 轴相电流（安培）
- iq_mtpa — 对应于 MTPA 的 q 轴相电流（安培）
- Ld — d 轴绕组电感（亨）
- Lq — q 轴绕组电感（亨）
- imax — 电机的最大相电流（峰值）（安培）
- vmax — 供给电机的相对于中性点电压（峰值）的基波最大值（伏特）
- vdo — 当 id 为零时的 d 轴电压（伏特）
- vqo — 当 iq 为零时的 q 轴电压（伏特）
- ωe — 对应于定子电压频率的电角速度（弧度/秒）
- id — d 轴电流（安培）
- iq — q 轴电流（安培）
- id_fw — d 轴弱磁电流（安培）
- iq_fw — q 轴弱磁电流（安培）
- ωbase — 电机的机械基转速（弧度/秒）

## 示例

PMSM 的弱磁控制（使用 MTPA）

## 端口

### 输入

**Tref — 参考转矩值**（标量）

模块为其计算参考电流的参考转矩输入值。此端口的单位取决于**输入单位**参数值。如果将此参数设置为 **SI 单位**，则此端口将接受以 Nm 为单位的输入信号。

数据类型: single | double | fixed point

**⍵m — 机械转速**（标量）

模块为其计算参考电流的参考机械转速值。此端口的单位取决于**输入单位**参数值。如果将此参数设置为 **SI 单位**，则此端口将接受以机械弧度/秒为单位的输入信号。

数据类型: single | double | fixed point

**Vdc — DC 母线电压**（标量）

可变 DC 母线电压（伏特）。此端口的单位取决于**输入单位**参数值。如果将此参数设置为 **SI 单位**，则此端口将接受以伏特为单位的输入信号。

依赖关系：要启用此端口，请将**电机类型**设置为**内置式 PMSM**，并将 **Vdc 输入方法**设置为**输入端口**。

数据类型: single | double | fixed point

### 输出

**Idref — 参考 d 轴电流**（标量）

参考 d 轴相电流，可高效生成输入转矩和转速值。

此端口的单位取决于由**输入单位**参数定义的模块输入单位。如果将此参数设置为 **SI 单位**，则此端口将输出以安培为单位的信号。

数据类型: single | double | fixed point

**Iqref — 参考 q 轴电流**（标量）

参考 q 轴相电流，可高效生成输入转矩和转速值。

此端口的单位取决于由**输入单位**参数定义的模块输入单位。如果将此参数设置为 **SI 单位**，则此端口将输出以安培为单位的信号。

数据类型: single | double | fixed point

## 参数

### 电机参数

**电机类型 — PMSM 的类型**
内置式 PMSM（默认）| 表贴式 PMSM

基于永磁体位置的 PMSM 的类型。

**极对数 — 可用极对数**
4（默认）| 标量

电机中可用的极对数。

**每相定子电阻(欧姆) — 定子相绕组的电阻（欧姆）**
0.36（默认）| 标量

定子相绕组的电阻（以 ohm 为单位）。

依赖关系：要启用此参数，请将**电机类型**设置为**内置式 PMSM**。

**定子 d 轴电感(H) — d 轴定子绕组电感**
0.2e-3（默认）| 标量

沿旋转 dq 参考系的 d 轴的定子绕组电感（以亨为单位）。

**定子 q 轴电感(H) — q 轴定子绕组电感**
0.4e-3（默认）| 标量

沿旋转 dq 参考系的 q 轴的定子绕组电感（以亨为单位）。

依赖关系：要启用此参数，请将**电机类型**设置为**内置式 PMSM**。

**永磁磁链(Wb) — 永磁体的磁通链**
6.4e-3（默认）| 标量

定子绕组和转子上永磁体之间的磁通链（韦伯）。

**最大电流(A) — 电机的相电流最大限值（安培）**
7.1（默认）| 标量

电机的最大相电流限值（安培）。

**Vdc 输入方法 — Vdc 的输入方法**
通过对话框指定（默认）| 输入端口

可以使用下列方法之一来指定 Vdc 输入。

- **通过对话框指定** - 使用参数 **DC 电压(V)** 指定固定参考电压 Vdc。
- **输入端口** - 使用输入端口 **Vdc** 指定可变参考电压 Vdc。

注意：如果您为 Vdc 选择**输入端口**输入方法，请确保在**输入单位**选项卡中配置**基电压(V)** 参数。

依赖关系：要启用此参数，请将**电机类型**设置为**内置式 PMSM**。

**DC 电压(V) — DC 母线电压（伏特）**
24（默认）| 标量

DC 母线电压（以伏特为单位）。

依赖关系：要启用此参数，请将**电机类型**设置为**内置式 PMSM**，并将 **Vdc 输入方法**设置为**通过对话框指定**。

### 输入单位

**输入信号单位 — 模块输入值的单位**
标幺(PU)（默认）| SI 单位

模块输入值的单位。

**基转速(rpm) — 电机的基转速 (rpm)**
4107（默认）| 标量

弱磁区外额定电压和额定电流下的电机转速（以 rpm 为单位）。

依赖关系：要启用此参数，请使用如下任一设置：

- 将**输入信号单位**参数设置为**标幺(PU)**。
- 或将**电机类型**参数设置为**表贴式 PMSM**。对于表贴式 PMSM，您必须指定基转速（即使在使用 SI 单位时），以便模块可以确定转速阈值。

**基电流(A) — 标幺转换的基电流（安培）**
19.3（默认）| 标量

对应于 1 标幺的电流（以安培为单位）。我们建议您使用模数转换器 (ADC) 检测到的最大电流作为基电流。

依赖关系：要启用此参数，请将**输入信号单位**设置为**标幺(PU)**。

**基转矩(Nm) — 标幺转换的基转矩 (Nm)**
0.74112（默认）| 标量

对应于 1 标幺的转矩（以 Nm 为单位）。有关详细信息，请参阅标幺制页。

您无法指定此值。该模块使用其他参数在内部计算此值。

依赖关系：要显示此参数，请将**输入信号单位**设置为**标幺(PU)**。

**基电压(V) — 标幺转换的基电压（伏特）**
24/sqrt(3)（默认）| 标量

对应于 1 标幺的电压（以伏特为单位）。有关详细信息，请参阅标幺制页。

您无法指定此值。该模块使用其他参数在内部计算此值。

依赖关系：要显示此参数，请将**输入信号单位**设置为**标幺(PU)**。

### 实现

**优先执行时间 — 缩减计算量以减少算法执行时间**
on（默认）| off

如果选择此参数，模块将遵循计算逼近来确定优先级并减少算法执行时间。清除此字段可在不使用逼近的情况下以迭代方式运行模块算法。

## 参考

[1] B. Bose, Modern Power Electronics and AC Drives. Prentice Hall, 2001. ISBN-0-13-016743-6.

[2] Morimoto, Shigeo, Masayuka Sanada, and Yoji Takeda. "Wide-speed operation of interior permanent magnet synchronous motors with high-performance current regulator." IEEE Transactions on Industry Applications, Vol. 30, Issue 4, July/August 1994, pp. 920-926.

[3] Li, Muyang. "Flux-Weakening Control for Permanent-Magnet Synchronous Motors Based on Z-Source Inverters." Master's Thesis, Marquette University, e-Publications@Marquette, Fall 2014.

[4] Briz, Fernando, Michael W. Degner, and Robert D. Lorenz. "Analysis and design of current regulators using complex vectors." IEEE Transactions on Industry Applications, Vol. 36, Issue 3, May/June 2000, pp. 817-825.

[5] Lorenz, Robert D., Thomas Lipo, and Donald W. Novotny. "Motion control with induction motors." Proceedings of the IEEE, Vol. 82, Issue 8, August 1994, pp. 1215-1240.

[6] Briz, Fernando, et al. "Current and flux regulation in field-weakening operation [of induction motors]." IEEE Transactions on Industry Applications, Vol. 37, Issue 1, Jan/Feb 2001, pp. 42-50.

[7] TI Application Note, "Sensorless-FOC With Flux-Weakening and MTPA for IPMSM Motor Drives."

[8] Haque, M. E., L. Zhong, and M. F. Rahman. "Improved trajectory control for an interior permanent magnet synchronous motor drive with extended operating limit." Journal of Electrical & Electronics Engineering. Vol. 22, Number 1, 2003, p. 49.

## 扩展功能

### C/C++ 代码生成
使用 Simulink® Coder™ 生成 C 代码和 C++ 代码。

### 定点转换
使用 Fixed-Point Designer™ 设计和仿真定点系统。

## 版本历史记录

在 R2020a 中推出
