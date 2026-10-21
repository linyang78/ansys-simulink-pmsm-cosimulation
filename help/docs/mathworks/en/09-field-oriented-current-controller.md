# Field-Oriented Current Controller (Block)

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ref/fieldorientedcurrentcontroller.html`
> Archived: 2026-10-21 · R2026b · Since R2023b · Chinese version: `zh/09-field-oriented-current-controller.md`
> Libraries: Motor Control Blockset / Control / Induction Machine / Controllers
>            Motor Control Blockset / Control / Synchronous Machine / Controllers

---

## Description

Implement current control for three-phase motors using field-oriented control (FOC) technique.

The Field-Oriented Current Controller block implements current control for a three-phase permanent magnet
synchronous motor (PMSM) or an AC induction motor (ACIM) using the FOC algorithm. You can input the reference
*d*- and *q*-axis currents, measured stator phase *a* and *b* currents, motor electrical position, as well as
PI controller parameters to compute three phase voltages that drive the motor.

The block uses Clarke and Park transformations to compute actual *d*- and *q*-axis currents from the measured
phase currents and motor electrical position. It uses the PI Controller blocks to implement *d*- and *q*-axis
current controllers. The current controller loop uses the reference and actual *d*- and *q*-axis currents to
generate reference voltages that drive the motor. For more information about the FOC algorithm implemented by
the block, see *Field-Oriented Control*.

The block supports SI and per-unit inputs, however, **units of all block inputs should be identical**.

---

## Examples

| Example | Content |
|---|---|
| Swap Motors with Single Model Deployment of Sensor-Based FOC Algorithm | Run a PMSM with sensor-based FOC in industrial drives, swap motors at runtime without redeploying (nameplate-parameter adaptation) |
| Swap Motors with Single Deployment of Sensorless FOC Algorithm | Same, but sensorless (position estimated by Flux Observer) |
| Generate Motor Control Models for Selected Algorithm and Hardware | Generate Simulink® models for a selected algorithm and hardware |

---

## Ports

### Input

| Port | Type | Description |
|---|---|---|
| **IdqRef** | Vector | Reference *d*/*q* axis currents, `IdqRef = [IdRef, IqRef]` |
| **IabMeas** | Vector | Measured phase-a and phase-b currents, `IabMeas = [IaMeas, IbMeas]` |
| **θe** | Scalar | Motor electrical position (unit set by parameter) |
| **VSatLim** | Scalar | Saturation limit for the *d-q* reference voltages. Depends on DC bus and PWM method: `Vdc/2` for SPWM, `Vdc/√3` for SVM |
| **Kp,Ki·Ts** | Vector | *d*/*q* axis PI gains (Kp, Ki) with sampling time Ts multiplexed: `[Kp(d), Ki·Ts(d), Kp(q), Ki·Ts(q)]` |
| **PIConfig** | Vector | PI integrator initial values and limits: `[upper limit, lower limit, d-axis integrator initial value, q-axis integrator initial value]` |
| **Enable** | Scalar | `1` enables output; `0` resets the internal PI (note: Vabc may hold its previously computed value) |

Data Types: all support `single` | `double` | `fixed point`

### Output

| Port | Type | Description |
|---|---|---|
| **Vabc** | Vector | Three-phase voltages that drive the motor |
| **Debug** | Vector | Debug multiplexed signals: *Idq* (measured d/q currents), *Vdq* (PI output voltages), *Vαβ* (inverse Park voltages), *Iαβ* (Clarke currents) |

---

## Parameters

| Parameter | Value | Description |
|---|---|---|
| **Input electrical position unit** | `Radians` (default) \| `Degrees` \| `Per-unit` | Unit of the electrical position input |
| **Number of data points for sine-cosine lookup table** | `1024` (default, range [125, 4095]) | Size of the internal sin/cos lookup table (saves computation on fixed-point targets) |
| **Alpha (phase-a) axis alignment** | `D-axis` (default) \| `Q-axis` | Whether the α axis aligns with the d or q axis |
| **Saturation method** | `D-Q equivalence` (default) \| `Prioritize D axis` \| `Prioritize Q axis` | Strategy applied when the voltage saturates |
| **PWM method** | `SVM` (default) \| `SPWM` | Determines the VSatLim reference |

### Saturation methods explained

- **`D-Q equivalence`** — vd and vq are scaled by the same factor, preserving the vector direction. This is
  the standard choice; behavior in the field-weakening region stays predictable.
- **`Prioritize D axis`** — preserves the d axis (flux / field-weakening current) at the expense of the q axis.
- **`Prioritize Q axis`** — preserves the q axis (torque) at the expense of the d axis.

---

## Extended Capabilities

- **C/C++ Code Generation** — Generate C and C++ code using Simulink® Coder™
- **Fixed-Point Conversion** — Design and simulate fixed-point systems using Fixed-Point Designer™

## Version History

Introduced in R2023b

## See Also

PWM Reference Generator | PI Controller | Park Transform | Inverse Park Transform | Clarke Transform |
Sine-Cosine Lookup

**Topics**
- Open-Loop and Closed-Loop Motor Control Techniques
- Field-Oriented Control
