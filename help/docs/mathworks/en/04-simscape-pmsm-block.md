# PMSM (Simscape Electrical Block)

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/simscape-electrical/ref/pmsm.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/04-simscape-pmsm-block.md`
> Note: This is the motor plant block from Simscape Electrical, not a Motor Control Blockset control-algorithm
> block. It can be used to build the plant, as an alternative to the ECE model kept in Twin Builder.

---

## Description

The PMSM block models a permanent magnet synchronous motor (PMSM) with a three-phase wye-wound, delta-wound,
or open-ended stator. Use this block to model an interior PMSM (IPMSM), a surface PMSM (SPMSM), transverse
flux motor, an axial flux (pancake) motor, or a PMSM servomotor.

PMSMs have a permanent magnet rotor and a wound stator. You can use these motors in traction applications like
electric vehicles (EVs) and in actuation systems. In actuation systems, PMSMs are also called brushless
servomotors. A PMSM typically has a **sinusoidal back EMF profile** to reduce undesirable high-frequency
mechanical and electrical current harmonics compared to brushless direct current (BLDC) motors, which have a
trapezoidal back EMF profile.

The PMSM block models the motor with fixed d-axis and q-axis inductances, Ld and Lq. You can use this block to
model the two main types of PMSM:

- **SPMSM or SPM** — The rotor magnets are surface mounted. **Ld and Lq are equal.**
- **IPMSM or IPM** — The rotor magnets are interior to the rotor. **Ld and Lq are not equal.**

You can also categorize PMSMs based on the main flux paths. The main flux paths are commonly radial but can be
axial, which causes much higher torques for the same physical size of motor.

You can use the **Winding type** parameter to specify the configuration for the windings (wye-wound,
delta-wound, or open-end).

> [Figure: equivalent electrical circuit for a wye-wound stator]

Simscape™ Electrical™ includes several blocks that can model the same type of motor or actuator. Choose a
block that has sufficient modeling detail for the engineering design questions that you need to answer. Do not
use a block that has more modeling detail than you need, because higher-fidelity models slow down simulation
and are more complex to parameterize.

Blocks like the PMSM block model motors with fixed or parameter-dependent coefficients with a simple
equivalent circuit. These models have an intermediate level of fidelity. Use this block to design controls or
systems in actuation applications, such as robotics and mechatronics, and for efficiency predictions when
saturation and harmonics only weakly impact losses.

---

## Motor Construction

> [Figure: motor construction with a single pole-pair on the rotor]

Permanent magnets generate a rotor magnetic field that creates a sinusoidal rate of change of flux based on
the rotor angle.

For the axes convention, when you set the **Rotor angle definition** parameter to *Angle between the a-phase
magnetic axis and the d-axis*, the a-phase and permanent magnet fluxes align when the rotor mechanical angle,
θr, is zero. When you set the **Rotor angle definition** parameter to *Angle between the a-phase magnetic axis
and the q-axis*, the rotor mechanical angle is the angle between the a-phase magnetic axis and the rotor q-axis.

---

## Equations

Voltages across the stator windings are:

```
[va]   [Rs  0   0 ] [ia]   [dψa/dt]
[vb] = [0   Rs  0 ] [ib] + [dψb/dt]
[vc]   [0   0   Rs] [ic]   [dψc/dt]
```

where va, vb, vc are the individual phase voltages across the stator windings; Rs is the equivalent resistance
of each stator winding; ia, ib, ic are the currents flowing in the stator windings; and dψa/dt, dψb/dt, dψc/dt
are the rates of change for the magnetic flux in each stator winding.

The permanent magnet and the three windings contribute to the total flux linking each winding. The total flux is:

```
[ψa]   [Laa Lab Lac] [ia]   [ψam]
[ψb] = [Lba Lbb Lbc] [ib] + [ψbm]
[ψc]   [Lca Lcb Lcc] [ic]   [ψcm]
```

where Laa, Lbb, Lcc are the self-inductances of the stator windings; Lab, Lac, Lba, and so on are the mutual
inductances; and ψam, ψbm, ψcm are the permanent magnet fluxes linking the stator windings.

The inductances in the stator windings are functions of the rotor electrical angle and defined by:

```
θe = N·θr + rotor offset

Laa = Ls + Lm·cos(2θe)
Lbb = Ls + Lm·cos(2(θe − 2π/3))
Lcc = Ls + Lm·cos(2(θe + 2π/3))

Lab = Lba = −Ms − Lm·cos(2(θe + π/6))
Lbc = Lcb = −Ms − Lm·cos(2(θe + π/6 − 2π/3))
Lca = Lac = −Ms − Lm·cos(2(θe + π/6 + 2π/3))
```

where θr is the rotor mechanical angle; θe is the rotor electrical angle; rotor offset is 0 if the rotor
electrical angle is defined with respect to the d-axis, or −π/2 if defined with respect to the q-axis;
Ls is the stator self-inductance per phase (the average self-inductance); Lm is the stator inductance
fluctuation; Ms is the stator mutual inductance (average).

The permanent magnet flux linking winding a is a maximum when θe = 0° and zero when θe = 90°. Therefore, the
linked motor flux is defined by:

```
[ψam]   [ψm·cos(θe)        ]
[ψbm] = [ψm·cos(θe − 2π/3) ]
[ψcm]   [ψm·cos(θe + 2π/3) ]
```

where ψm is the permanent magnet flux linkage.

---

## Simplified Electrical Equations

Applying Park's transformation to the block electrical equations produces an expression for torque that is
independent of the rotor angle. Park's transformation is defined by:

```
P = (2/3) × [ cos θe        cos(θe−2π/3)        cos(θe+2π/3)  ]
            [ −sin θe       −sin(θe−2π/3)       −sin(θe+2π/3) ]
            [ 0.5           0.5                 0.5           ]
```

where θe is the electrical angle defined as N·θr. N is the number of pole pairs.

Using Park's transformation on the stator winding voltages and currents transforms them to the dq0 frame,
which is independent of the rotor angle:

```
[vd]       [va]
[vq] = P × [vb]
[v0]       [vc]

[id]       [ia]
[iq] = P × [ib]
[i0]       [ic]
```

Applying Park's transformation to the first two electrical equations produces these equations that define the
block behavior:

```
vd = Rs·id + Ld·did/dt − N·ω·iq·Lq
vq = Rs·iq + Lq·diq/dt + N·ω·(id·Ld + ψm)
v0 = Rs·i0 + L0·di0/dt

T = (3/2)·N·( iq·(id·Ld + ψm) − id·iq·Lq )
```

where:

- `Ld = Ls + Ms + (3/2)·Lm` — d-axis stator inductance
- `Lq = Ls + Ms − (3/2)·Lm` — q-axis stator inductance
- `L0 = Ls − 2·Ms` — stator zero-sequence inductance
- ω is the rotor mechanical rotational speed
- N is the number of rotor permanent magnet pole pairs
- T is the rotor torque (flows from the motor case, port C, to the motor rotor, port R)

The PMSM block uses the **original, non-orthogonal implementation** of the Park transform. If you try to apply
the alternative implementation, you get different results for the dq0 voltage and currents.

---

## Alternative Flux Linkage Parameterization

You can parameterize the motor using the back EMF or torque constants which are more commonly given on motor
datasheets by using the **Permanent magnet flux linkage** parameter.

The back EMF constant is the peak voltage induced by the permanent magnet in the per-unit rotational speed of
each of the phases. The relationship between the peak permanent magnet flux linkage and the back EMF is:

```
ke = N·ψm
```

The back EMF, eph, for one phase is:

```
eph = ke·ω
```

The torque constant is the peak torque induced by the per-unit current of each of the phases. It is
**numerically identical in value** to the back EMF constant when both are expressed in SI units:

```
kt = N·ψm
```

When Ld = Lq and the currents in all three phases are balanced, the combined torque T is:

```
T = (3/2)·kt·iq = (3/2)·kt·Ipk
```

where Ipk is the peak current in any of the three windings. The factor 3/2 follows from this being the
steady-state sum of the torques from all phases. Therefore, the torque constant kt can also be:

```
kt = (2/3)·(T / Ipk)
kt = (2/3)·(T / iline,rms)
```

---

## Calculating Iron Losses

Iron losses are divided into two terms, one representing the main magnetizing path, and the other representing
the cross-tooth tip path that becomes active during field weakened operation.

The term representing the main magnetizing path depends on the induced RMS line-to-neutral stator voltage,
Vmrms:

```
POC(Vmrms) = ah·k·Vmrms + aj·k²·Vmrms² + aex·k^1.5·Vmrms^1.5
```

This is the dominant term during no-load operation. k is the back EMF constant relating RMS volts per Hz,
defined as k = Vmrms/f, where f is the electrical frequency. The first term is the magnetic hysteresis loss,
the second is the eddy current loss and the third is the excess loss.

The term representing the cross-tooth tip path becomes important when a demagnetizing field is set up and can
be determined from a finite element analysis short-circuit test:

```
PSC(Vdrms*) = bh·k·Vdrms* + bj·k²·Vdrms*² + bex·k^1.5·Vdrms*^1.5
```

---

## Predefined Parameterization

There are multiple available built-in parameterizations for the PMSM block. This pre-parameterization data
allows you to set up the block to represent components by specific suppliers.

To load a predefined parameterization, double-click the PMSM block, click the `<click to select>` hyperlink of
the **Selected part** parameter and, in the Block Parameterization Manager window, select the part.

**Note:** The predefined parameterizations of Simscape components use available data sources for the parameter
values. Engineering judgment and simplifying assumptions are used to fill in for missing data. As a result,
expect deviations between simulated and actual physical behavior. To ensure accuracy, validate the simulated
behavior against experimental data.

---

## Model Thermal Effects

You can expose thermal ports to model the effects of losses that convert power to heat. Set the **Modeling
option** parameter to either:

- **No thermal port** — The block contains expanded electrical conserving ports associated with the stator
  windings, but does not contain thermal ports.
- **Show thermal port** — The block contains expanded electrical conserving ports and thermal conserving ports
  for each of the windings and for the rotor.

---

## Generate Derived Data Sheet (Since R2026a)

You can generate a derived data sheet for the PMSM block that contains summary tables and characteristic plots
similar to those that device manufacturers provide in their data sheets.

The derived data sheet includes plots of:

- Torque and current versus rotor speed at peak torque and the maximum AC voltage.
- Torque, efficiency, shaft power, and stator current versus speed at 50% and 100% of the rated stator current.

To generate a derived data sheet:

1. Open the MATLAB script by clicking the **Open live script** button next to the **Derived data sheet**
   parameter in the **Utilities** section of the block dialog box.
2. In the script, specify values for: peak line current, peak maximum allowable line current, maximum stator
   line-to-line peak voltage, rated rotor speed, maximum rotor speed.
3. Click **Generate Data Sheet**.

---

## Key Parameters

| Parameter | Default | Notes |
|---|---|---|
| **Modeling option** | No thermal port | Whether to enable thermal ports |
| **Electrical connection** | Composite three-phase ports | Composite vs expanded ports |
| **Winding type** | Wye-wound | Wye-wound / Delta-wound / Open-end |
| **Modeling fidelity** | Constant Ld, Lq and PM | Constant vs **Tabulated Ld, Lq and PM** |
| **Number of pole pairs** | 6 | |
| **Permanent magnet flux linkage** | 0.03 Wb | |
| **Stator d-axis inductance, Ld** | 0.00022 H | |
| **Stator q-axis inductance, Lq** | 0.00022 H | |
| **Direct-axis current vector, iD** | [-200, 0, 200] A | For tabulated mode |
| **Quadrature-axis current vector, iQ** | [-200, 0, 200] A | For tabulated mode |
| **Ld matrix, Ld(id,iq)** | 0.0002·ones(3,3) H | For tabulated mode |
| **Lq matrix, Lq(id,iq)** | 0.0002·ones(3,3) H | For tabulated mode |
| **Permanent magnet flux linkage, PM(id,iq)** | 0.1·ones(3,3) Wb | For tabulated mode |
| **Stator resistance per phase, Rs** | 0.013 Ohm | |
| **Rotor angle definition** | Angle between the a-phase magnetic axis and the d-axis | Must match the ECE convention |
| **Rotor inertia** | 0.01 kg·m² | |
| **Rotor damping** | 0 N·m/(rad/s) | |

---

## Examples

- Electric Power Assisted Steering
- **Model Faulted PMSM** — Model a faulted PMSM at winding-slot level (requires magnetic-domain modeling)
- Model a Three-Phase PMSM Drive
- Three-Phase PMSM Drive with Thermal Model
- Parameterize a Permanent Magnet Synchronous Motor
- **IPMSM Torque Control** — Open-loop torque + closed-loop current
- **IPMSM Velocity Control** — Outer speed loop + two inner current loops, Stateflow task scheduling
- IPMSM Torque-Based Load Control
- Control Velocity of Three-Phase PMSM with Open-End Winding (Since R2025a)
- IPMSM Outer Loop Controller Evaluation

---

## See Also

**Simscape Blocks:** BLDC | FEM-Parameterized PMSM | FEM-Parameterized Synchronous Machine | Hybrid
Excitation PMSM | Magnetic Rotor | Motor & Drive (System Level) | PMSM (DQ0) | Rotating Air Gap

**Topics:** Simscape Electrical Part Collection | Choose Blocks to Model Motors or Actuators | Expand and
Collapse Three-Phase Ports on a Block

## References

[1] Kundur, P. *Power System Stability and Control*. New York, NY: McGraw Hill, 1993.

[2] Anderson, P. M. *Analysis of Faulted Power Systems*. Hoboken, NJ: Wiley-IEEE Press, 1995.

[3] Mellor, P.H., R. Wrobel, and D. Holliday. "A computationally efficient iron loss model for brushless AC
machines that caters for rated flux and field weakened operation." IEEE Electric Machines and Drives
Conference. May 2009.
