# PMSM Drive Characteristics and Constraint Curves

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ug/pmsm-characteristics-constraint-curves.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/03-pmsm-characteristics-constraint-curves.md`
> Note: Official text transcribed paragraph by paragraph. Code blocks are the official Live Script examples.

---

## Overview

This example uses Motor Control Blockset™ to show how to use the PMSM characteristic plotting and PMSM
milestone speed identification functions to obtain a control trajectory.

**Required MathWorks Products:** Motor Control Blockset, Simulink

---

## PMSM Types and d-q Axes

The permanent magnet synchronous motors (PMSMs) come in different configurations.

- When the permanent magnets (PMs) are mounted on the surface of the rotor, the motor is called a
  **surface-mounted PMSM (SPMSM)**.
- When the PMs are embedded inside the rotor below the surface, the motor is called an
  **interior PMSM (IPMSM)**.

In the d-q rotor reference frame for PMSMs, the **d-axis** is the axis parallel to the rotor's magnetic
orientation and the **q-axis** is the perpendicular axis, leading the d-axis. An SPMSM has equal d-axis
and q-axis inductances. **An IPMSM has a higher q-axis inductance than its d-axis inductance.** This helps
the IPMSM to utilize the reluctance torque in addition to the magnetic torque.

---

## Corner Speed and Base Speed

The **corner speed** of a PMSM is the speed at which the torque-vs-speed (drive characteristics) curve of
the PMSM changes shape (has a corner) for a given current limit. When you plot the drive characteristics
for rated torque (at rated current), the corner speed is also known as the **rated speed** or **base speed**.

---

## Constraint Curves

You draw the constraint curves for a PMSM to understand the possible operational area and boundaries.

- **MTPA trajectory** of an IPMSM provides the highest torque for the allowed stator current.
- **MTPV trajectory** of an IPMSM provides the highest torque while satisfying the stator voltage constraint.
- **Voltage limit curve** (ellipse for an IPMSM or circle for SPMSM) is centered around a point that is
  called the **characteristic current**. This curve **shrinks with increasing rotor speed**.

---

## Three Segments

### Segment I (Constant Torque Region)

To begin the operation, the motor increases the torque from zero to the rated torque. The operating point
shifts from point O to A along the MTPA trajectory (line segment OA). This corresponds to the id and iq
values at the tip of MTPA. The motor speed ω1, at which the voltage limit ellipse touches the MTPA curve
and the current limit circle, is the rated speed. This is the first milestone speed of the characteristic curve.

### Segment II (Field Weakening, Current Limited)

At the operating point A, the control reaches the maximum possible current, and the field weakening strategy
begins. The current trajectory moves along the current limit circle while maintaining the current constraint
from point A to B (line segment AB). The operating point B is the speed at which the voltage ellipse touches
the current limit circle and the MTPV curve. This is the second milestone speed.

### Segment III (MTPV Region)

Beyond the point B, the voltage ellipse shrinks further and the MTPV trajectory provides the optimal torque
until the maximum speed is reached at the operating point C (line segment BC). The theoretical maximum speed
for a friction-free motor with MTPV is infinite. Practically, the frictional components in the motor limit
the maximum speed to a finite value. In Motor Control Blockset software, the maximum speed, including the
friction, is when the frictional torque balances the motor torque produced at that speed.

The calculated maximum speed is the **third milestone speed**. In some motor configurations, MTPV is not
possible. In such cases, the frictional torque limits the operating point B, and there is no operating
point C. Such motors have **two milestone speeds**.

---

## Milestone Speeds

To get all the milestone speeds of the PMSM, use the `mcb.PMSMSpeeds` function. The operable speeds are
different for different field weakening control (FWC) strategies. The default FWC method is set to voltage
current limited maximum torque (**VCLMT**) control, also called optimal current vector control. The function
returns the speed values in **rpm**.

```matlab
inverter.V_dc = 24;
pmsm = mcb.getPMSMParameters('BLY171D');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter);
disp(milestone_speeds);
%   5393
%   9373
```

With a higher rated current the third segment (MTPV) becomes reachable:

```matlab
pmsm.I_rated = 8;   % Assuming a higher I_rated to be able to get MTPV trajectory
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter);
disp(milestone_speeds);
%   2342
%   2958
%   24369
```

### Speed Milestones with Different FW Methods

| FWCMethod | Milestone speeds (rpm) | Note |
|---|---|---|
| `vclmt` | 5393 / 9373 | Default, optimal current vector control |
| `cvcp` | 5393 / 7008 / 8361 | Constant voltage constant power |
| `cccp` | 5393 / 7008 | Constant current constant power |
| `none` | 5393 / 6226 | id always 0, no field weakening |

```matlab
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'vclmt');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'cvcp');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'cccp');
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter, 'verbose', 0, 'FWCMethod', 'none');
```

### Currents at Milestone Speeds

Each command outputs the array with columns for each milestone speed, and each row of the column provides
**id, iq, and speed (in electrical rad/s)**.

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

## Plot Drive Characteristics

The drive characteristics display the torque-vs-speed, power-vs-speed, and current-vs-speed characteristic
plots of a motor under the given operating constraints. Use the `mcb.PMSMCharacteristics` function to plot
the drive characteristics.

When you set the `driveCharacteristics` option to 2, the function plots an additional figure in the vd-vq
space with the voltage constraint curve and the voltage trajectory.

```matlab
inverter = mcb.getInverterParameters('BoostXL-DRV8305');
pmsm = mcb.getPMSMParameters('BLY171D');
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 2, 'constraintCurves', 1, 'FWCMethod', 'vclmt')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'cvcp')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'cccp')
mcb.PMSMCharacteristics(pmsm, inverter, 'driveCharacteristics', 1, 'constraintCurves', 1, 'FWCMethod', 'none')
```

### Plot Drive Characteristics for Imax

When the motor operates continuously supporting a constant load torque, that condition is the rated
operating condition, and the operating current is the rated current. The short-term rating of the motor is
higher than the continuous-current rating.

```matlab
mcb.PMSMCharacteristics(pmsm, inverter, "FWCMethod", "vclmt", "driveCharacteristics", 1, "imax", 8, "constraintCurves", 0)
```

---

## Customize Drive Characteristics

The `pmsm` structure expects values for the `p`, `Rs`, `Ld`, `Lq`, `FluxPM`, `B` and `I_rated` fields.
The `inverter` structure expects a value for the `V_dc` field.

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

## Constraint Curves in id-iq Space

```matlab
inverter = mcb.getInverterParameters('BoostXL-DRV8305');
pmsm = mcb.getPMSMParameters('BLY171D');
pmsm.Rs = 0.1;
pmsm.Lq = pmsm.Ld * 1.8;
w_rpm = 5000;
T_load = 0;
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', w_rpm, 'torque', T_load);
```

### At Maximum Speed

The constraint curves provide a secondary check for whether the calculated speeds are correct. When you
plot the constraint curves at maximum speed, the plot shows three intersecting curves: current limit circle,
voltage limit curve, and constant torque curve.

```matlab
milestone_speeds = mcb.PMSMSpeeds(pmsm, inverter);
mcb.PMSMCharacteristics(pmsm, inverter, 'speed', milestone_speeds(end), torque = 0)
```

### At Milestone Speeds

In addition to the intersecting curves at maximum speed, notice that at the corner speed, the MTPA curve,
the current limit circle, and the voltage constraint curve intersect.

```matlab
[milestone_speeds] = mcb.PMSMSpeeds(pmsm, inverter, 'constraintCurves', 1);
disp(milestone_speeds);
%   5645
%   9641
```

### Different Speeds in Same Figure

Use the `opacity` option to set the opacity of the presently plotted constraint curve.

- When you set `opacity` to 1 (default), the function creates a new figure window for plotting.
- When you set `opacity` to a value less than 1 (but more than 0), the function plots the voltage
  constraint, MTPA, and MTPV curves with changing opacity.

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

## Actual vs Approximate Voltage Equations

Usually, the PMSM characteristic equations for vd and vq have an i×r term, which the computations ignore
because this value becomes negligible at higher speeds. In this example, you can include or exclude the i×r
term from the vd and vq equations while calculating the maximum speeds. The actual form of the equation is
as follows.

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

The actual equation gives 9373 rpm at maximum speed while the approximate one gives only 8775 rpm —
a difference of about **6.8%**.

---

## Case Studies: IPMSM and SPMSM

This section provides case studies that show how to find a possible control trajectory for an IPMSM and
SPMSM. The workflow:

1. Plot drive characteristics (including MTPV) and constraint curves at the **corner speed**.
2. Plot constraint curves with `driveCharacteristics`=0, `opacity`=0.5 at the speed where **MTPV starts**.
3. Plot constraint curves with `driveCharacteristics`=0, `opacity`=0.3 at the **maximum speed**.

When the motor resistance is high enough, the MTPV curve shifts dynamically along with the speed,
resulting in the current trajectory not following any single MTPV curve. The resulting cyan curve is the
**achievable MTPV curve** because the example uses the actual equations to dynamically solve for operating
points and plot the curves.

```matlab
% IPMSM case
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

% SPMSM case (Lq = Ld)
pmsm.Lq = pmsm.Ld;
```

---

## See Also

- PMSM Constraint Curves and Their Application
- SynRM Constraint Curves and Their Application
- Field-Weakening Control (with MTPA) of Nonlinear PMSM Using Lookup Table

## References

[1] Mihailovic, Zoran. "Modeling and Control Design of Vsi-Fed Pmsm Drive Systems With Active Load."
Thesis, Virginia Tech, 1998.

[2] Li, Muyang. "Flux-Weakening Control for Permanent-Magnet Synchronous Motors Based on Z-Source
Inverters." Thesis, 2014.
