# MTPA Control Reference

> **官方原文存档** —— 来源 `https://www.mathworks.com/help/mcb/ref/mtpacontrolreference.html`
> 存档日期：2026-10-21 · 版本标注 R2026b · 中文版见 `mtpacontrolreference.zh-CN.md`
> 说明：本文件为官方页面正文的**逐段照录**，公式按纯文本还原（原页面为图片/MathML，网页转文本时会散架）。
> 数学符号以 `Xxx_mtpa` 这类下划线形式保留，与原文一致。

---

Compute reference currents for maximum torque per ampere (MTPA) and field-weakening operation

**Libraries:** Motor Control Blockset / Control / Synchronous Machine / Control Reference

## Description

The MTPA Control Reference block computes the d-axis and q-axis reference current values for maximum torque per ampere (MTPA) and field-weakening operations. The computed reference current values result in efficient output for the permanent magnet synchronous motor (PMSM).

You can specify the reference torque and feedback mechanical speed and the block outputs the corresponding d- and q-axes reference current values for MTPA and field-weakening operations. For a given mechanical speed, in addition to the highest possible torque values, the block also supports
reference torque values that are less than the rated torque of a PMSM.

The block computes the reference current values by solving mathematical relationships.

In addition, you can use the **Vdc input method** parameter to configure the block to accept a fixed reference DC voltage through the **DC voltage (V)** parameter or a variable reference DC voltage through a separate input port **Vdc**.

These equations describe the computation of reference d-axis and q-axis current values by the block:

### Mathematical Model of PMSM

These model equations describe the dynamics of the PMSM in the rotor flux reference frame:

```
vd = id·Rs + dλd/dt − ωe·Lq·iq

vq = iq·Rs + dλq/dt + ωe·Ld·id + ωe·λpm

λd = Ld·id + λpm

λq = Lq·iq

Te = (3/2)·p·(λpm·iq + (Ld − Lq)·id·iq)

Te − TL = J·dωm/dt + B·ωm
```

where:

| 符号 | 含义 |
|---|---|
| vd | d-axis voltage (volts) |
| vq | q-axis voltage (volts) |
| id | d-axis current (amperes) |
| iq | q-axis current (amperes) |
| Rs | stator phase winding resistance (ohms) |
| λpm | permanent magnet flux linkage (weber) |
| λd | d-axis flux linkage (weber) |
| λq | q-axis flux linkage (weber) |
| ωe | electrical speed corresponding to frequency of stator voltages (radians/sec) |
| ωm | rotor mechanical speed (radians/sec) |
| Ld | d-axis winding inductance (henry) |
| Lq | q-axis winding inductance (henry) |
| Te | electromechanical torque produced by the PMSM (Nm) |
| TL | load torque (Nm) |
| p | number of motor pole pairs |
| J | inertia coefficient (kg-m2) |
| B | friction coefficient (kg-m2/sec) |

### Base Speed

Base speed is the maximum motor speed at the rated voltage and rated load, outside the field-weakening region. These equations describe the computation of the motor base speed.

The inverter voltage constraint is defined by computing the d-axis and q-axis voltages:

```
vdo = −ωe·Lq·iq

vqo = ωe·(Ld·id + λpm)

vmax = vdc/√3 − Rs·imax ≥ sqrt(vdo² + vqo²)
```

The current limit circle defines the current constraint which can be considered as:

```
imax² = id² + iq²
```

In the preceding equation, `id` is zero for surface PMSMs. For interior PMSMs, the block considers values of `id` and `iq` corresponding to MTPA.

Using these equations, we can compute the base speed as:

```
ωbase = (1/p) · vmax / sqrt( (Lq·iq)² + (Ld·id + λpm)² )
```

where:

- ωe — electrical speed corresponding to frequency of stator voltages (radians/sec)
- ωbase — mechanical base speed of the motor (radians/sec)
- id — d-axis current (amperes)
- iq — q-axis current (amperes)
- vdo — d-axis voltage when id is zero (volts)
- vqo — q-axis voltage when iq is zero (volts)
- Ld — d-axis winding inductance (henry)
- Lq — q-axis winding inductance (henry)
- Rs — stator phase winding resistance (ohms)
- λpm — permanent magnet flux linkage (weber)
- vd — d-axis voltage (volts)
- vq — q-axis voltage (volts)
- vmax — maximum fundamental line to neutral voltage (peak) supplied to the motor (volts)
- vdc — dc voltage supplied to the inverter (volts)
- imax — maximum phase current (peak) of the motor (amperes)
- p — number of motor pole pairs

### Surface PMSM

For a surface PMSM, you can achieve maximum torque by using zero d-axis current when the motor is below the base speed. For the field-weakening operation, the block calculates the reference d-axis current using the constant-voltage-constant-power control (CVCP) algorithm defined by these equations:

**If ωm ≤ ωbase:**

```
id_mtpa = 0
iq_mtpa = Tref / ((3/2)·p·λpm)
id_sat  = id_mtpa = 0
iq_sat  = sat(iq_mtpa, imax)
```

**If ωm > ωbase:**

```
id_fw  = (ωe_base − ωe)·λpm / (ωe·Ld)
id_sat = max(id_fw, −imax)
iq_fw  = Tref / ((3/2)·p·λpm)
iq_lim = sqrt(imax² − id_sat²)
iq_sat = sat(iq_fw, iq_lim)
```

The saturation function to compute `iq_sat` is:

```
If iq_fw < −iq_lim:   iq_sat = −iq_lim
If iq_fw >  iq_lim:   iq_sat =  iq_lim
If −iq_lim ≤ iq_fw ≥ iq_lim:  iq_sat = iq_fw
```

The block outputs these values:

```
Idref = id_sat
Iqref = iq_sat
```

where:

- ωe — electrical speed corresponding to frequency of stator voltages (radians/sec)
- ωm — rotor mechanical speed (radians/sec)
- ωbase — mechanical base speed of the motor (radians/sec)
- ωe_base — electrical base speed of the motor (radians/sec)
- id_mtpa — d-axis phase current corresponding to MTPA (amperes)
- iq_mtpa — q-axis phase current corresponding to MTPA (amperes)
- Tref — reference torque (Nm)
- p — number of motor pole pairs
- λpm — permanent magnet flux linkage (weber)
- id_fw — d-axis field weakening current (amperes)
- iq_fw — q-axis field weakening current (amperes)
- Ld — d-axis winding inductance (henry)
- imax — maximum phase current (peak) of the motor (amperes)
- id_sat — d-axis saturation current (amperes)
- iq_sat — q-axis saturation current (amperes)
- Idref — d-axis current corresponding to the reference torque and reference speed (amperes)
- Iqref — q-axis current corresponding to the reference torque and reference speed (amperes)

### Interior PMSM

For an interior PMSM, you can achieve maximum torque by computing the d-axis and q-axis reference currents from the torque equation. For the field-weakening operation, the block computes the reference d-axis current using the voltage and current limited maximum torque control (VCLMT) algorithm.

The reference currents for MTPA and field-weakening operations are defined by these equations:

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

These two equations describe the computation of field-weakening currents for maximum possible torque corresponding to a given speed value:

```
id_fw = −λpm/Ld + sqrt( (λpm/Ld)² − (Ld² − Lq²)·(λpm² + Lq²·imax² − (vmax/ωe)²) / (Ld² − Lq²) )

iq_fw = sqrt( imax² − id_fw² )
```

These two equations describe the computation of field-weakening currents for a given speed and torque value:

```
9·p²·(Ld − Lq)²·Lq²·ωe²·iq_fw⁴
 + (9·p²·λpm²·Lq²·ωe² − 9·p²·(Ld − Lq)²·vmax²)·iq_fw²
 − 12·Tref·p·λpm·Ld·Lq·ωe²·iq_fw
 + 4·(Tref)²·Ld²·ωe² = 0

id_fw = −λpm/Ld + (1/Ld)·sqrt( (vmax/ωe)² − (Lq·iq_fw)² )
```

To reduce the computation time, the block uses approximations to solve the preceding polynomial.

**If ωm ≤ ωbase:**

```
Idref = id_mtpa
Iqref = iq_mtpa
```

**If ωm > ωbase:**

```
Idref = max(id_fw, −imax)
iq_fw = sqrt( imax² − id_fw² )
If iq_fw < im:   Iqref = iq_fw
If iq_fw ≥ im:   Iqref = im
```

For negative reference torque values, the block updates the sign of `im` and `Iqref` and modifies the equations accordingly.

where:

- im_ref — estimated maximum current to produce the reference torque (amperes)
- im — saturated value of estimated maximum current (amperes)
- id_max — maximum d-axis phase current (peak) (amperes)
- iq_max — maximum q-axis phase current (peak) (amperes)
- Tref — reference torque (Nm)
- Idref — d-axis current component corresponding to the reference torque and reference speed (amperes)
- Iqref — q-axis current component corresponding to the reference torque and reference speed (amperes)
- p — number of motor pole pairs
- λpm — permanent magnet flux linkage (weber)
- id_mtpa — d-axis phase current corresponding to MTPA (amperes)
- iq_mtpa — q-axis phase current corresponding to MTPA (amperes)
- Ld — d-axis winding inductance (henry)
- Lq — q-axis winding inductance (henry)
- imax — maximum phase current (peak) of the motor (amperes)
- vmax — maximum fundamental line to neutral voltage (peak) supplied to the motor (volts)
- vdo — d-axis voltage when id is zero (volts)
- vqo — q-axis voltage when iq is zero (volts)
- ωe — electrical speed corresponding to frequency of stator voltages (radians/sec)
- id — d-axis current (amperes)
- iq — q-axis current (amperes)
- id_fw — d-axis field weakening current (amperes)
- iq_fw — q-axis field weakening current (amperes)
- ωbase — mechanical base speed of the motor (radians/sec)

## Examples

Field-Weakening Control (with MTPA) of PMSM

## Ports

### Input

**Tref — Reference torque value** (scalar)

Reference torque input value for which the block computes the reference current. The unit of this port depends on the **Input units** parameter value. If you set this parameter to **SI Units**, the port accepts input signal in Nm.

Data Types: single | double | fixed point

**⍵m — Mechanical speed** (scalar)

Reference mechanical speed value for which the block computes the reference current. The unit of this port depends on the **Input units** parameter value. If you set this parameter to **SI Units**, the port accepts input signal in mechanical radians/sec.

Data Types: single | double | fixed point

**Vdc — DC bus voltage** (scalar)

Variable DC bus voltage. The unit of this port depends on the **Input units** parameter value. If you set this parameter to **SI Units**, the port accepts input signal in volts.

Dependencies: To enable this port, set **Type of motor** to **Interior PMSM** and **Vdc input method** to **Input port**.

Data Types: single | double | fixed point

### Output

**Idref — Reference d-axis current** (scalar)

Reference d-axis phase current that can efficiently generate the input torque and speed values.

The unit of this port depends on the block input units defined by the **Input units** parameter. If you set this parameter to **SI Units**, the port outputs signal in amperes.

Data Types: single | double | fixed point

**Iqref — Reference q-axis current** (scalar)

Reference q-axis phase current that can efficiently generate the input torque and speed values.

The unit of this port depends on the block input units defined by the **Input units** parameter. If you set this parameter to **SI Units**, the port outputs signal in amperes.

Data Types: single | double | fixed point

## Parameters

### Motor Parameters

**Type of motor — Type of PMSM**
Interior PMSM (default) | Surface PMSM

Type of PMSM based on the location of the permanent magnets.

**Number of pole pairs — Number of available pole pairs**
4 (default) | scalar

Number of pole pairs available in the motor.

**Stator resistance per phase (Ohm) — Resistance of stator phase winding (ohms)**
0.36 (default) | scalar

Resistance of the stator phase winding (in ohms).

Dependencies: To enable this parameter, set **Type of motor** to **Interior PMSM**.

**Stator d-axis inductance (H) — d-axis stator winding inductance**
0.2e-3 (default) | scalar

Stator winding inductance (in henry) along the d-axis of the rotating dq reference frame.

**Stator q-axis inductance (H) — q-axis stator winding inductance**
0.4e-3 (default) | scalar

Stator winding inductance (in henry) along the q-axis of the rotating dq reference frame.

Dependencies: To enable this parameter, set **Type of motor** to **Interior PMSM**.

**Permanent magnet flux linkage (Wb) — Magnetic flux linkage of permanent magnets**
6.4e-3 (default) | scalar

Magnetic flux linkage (in weber) between the stator windings and permanent magnets on the rotor (weber).

**Max current (A) — Maximum phase current limit for motor (amperes)**
7.1 (default) | scalar

Maximum phase current limit for the motor (in amperes).

**Vdc input method — Input method for Vdc**
Specify via dialog (default) | Input port

Use one of these methods to specify the Vdc input.

- **Specify via dialog** — Specify the fixed reference voltage Vdc using the parameter **DC voltage (V)**.
- **Input port** — Specify the variable reference voltage Vdc using the input port **Vdc**.

Note: If you select the **Input port** input method for Vdc, ensure that you configure the **Base voltage (V)** parameter in the **Input Units** tab.

Dependencies: To enable this parameter, set **Type of motor** to **Interior PMSM**.

**DC voltage (V) — DC bus voltage (volts)**
24 (default) | scalar

DC bus voltage (in volts).

Dependencies: To enable this parameter, set **Type of motor** to **Interior PMSM** and **Vdc input method** to **Specify via dialog**.

### Input Units

**Input signal units — Unit of block input values**
Per-Unit (PU) (default) | SI Units

Unit of the block input values.

**Base speed (rpm) — Base speed of motor (rpm)**
4107 (default) | scalar

Speed of the motor (in rpm) at the rated voltage and rated current outside the field-weakening region.

Dependencies: To enable this parameter, either:

- Set **Input signal units** to **Per-Unit (PU)**.
- or Set **Type of motor** to **Surface PMSM**. For a surface PMSM, you must specify the base speed (even when using SI units) so that the block can determine the speed threshold.

**Base current (A) — Base current for per-unit conversion (amperes)**
19.3 (default) | scalar

Current (in amperes) corresponding to 1 per-unit. We recommend that you use the maximum current detected by an analog to digital converter (ADC) as the base current.

Dependencies: To enable this parameter, set **Input signal units** to **Per-Unit (PU)**.

**Base torque (Nm) — Base torque for per-unit conversion (Nm)**
0.74112 (default) | scalar

Torque (in Nm) corresponding to 1 per-unit. See Per-Unit System page for more details.

You cannot specify this value. The block computes this value internally using other parameters.

Dependencies: To display this parameter, set **Input signal units** to **Per-Unit (PU)**.

**Base voltage (V) — Base voltage for per-unit conversion (volts)**
24/sqrt(3) (default) | scalar

Voltage (in volts) corresponding to 1 per-unit. See Per-Unit System page for more details.

You cannot specify this value. The block computes this value internally using other parameters.

Dependencies: To display this parameter, set **Input signal units** to **Per-Unit (PU)**.

### Implementation

**Prioritise execution time — Scale down computations to reduce algorithm execution time**
on (default) | off

If you select this parameter, the block follows computational approximations to prioritize and reduce the algorithm execution time. Clear this field to run the block algorithms iteratively without using approximations.

## References

[1] B. Bose, Modern Power Electronics and AC Drives. Prentice Hall, 2001. ISBN-0-13-016743-6.

[2] Morimoto, Shigeo, Masayuka Sanada, and Yoji Takeda. "Wide-speed operation of interior permanent magnet synchronous motors with high-performance current regulator." IEEE Transactions on Industry Applications, Vol. 30, Issue 4, July/August 1994, pp. 920-926.

[3] Li, Muyang. "Flux-Weakening Control for Permanent-Magnet Synchronous Motors Based on Z-Source Inverters." Master's Thesis, Marquette University, e-Publications@Marquette, Fall 2014.

[4] Briz, Fernando, Michael W. Degner, and Robert D. Lorenz. "Analysis and design of current regulators using complex vectors." IEEE Transactions on Industry Applications, Vol. 36, Issue 3, May/June 2000, pp. 817-825.

[5] Lorenz, Robert D., Thomas Lipo, and Donald W. Novotny. "Motion control with induction motors." Proceedings of the IEEE, Vol. 82, Issue 8, August 1994, pp. 1215-1240.

[6] Briz, Fernando, et al. "Current and flux regulation in field-weakening operation [of induction motors]." IEEE Transactions on Industry Applications, Vol. 37, Issue 1, Jan/Feb 2001, pp. 42-50.

[7] TI Application Note, "Sensorless-FOC With Flux-Weakening and MTPA for IPMSM Motor Drives."

[8] Haque, M. E., L. Zhong, and M. F. Rahman. "Improved trajectory control for an interior permanent magnet synchronous motor drive with extended operating limit." Journal of Electrical & Electronics Engineering. Vol. 22, Number 1, 2003, p. 49.

## Extended Capabilities

### C/C++ Code Generation
Generate C and C++ code using Simulink® Coder™.

### Fixed-Point Conversion
Design and simulate fixed-point systems using Fixed-Point Designer™.

## Version History

Introduced in R2020a
