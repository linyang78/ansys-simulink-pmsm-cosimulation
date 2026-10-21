# LUT based PMSM Control Reference (Block)

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ref/lutbasedpmsmcontrolreference.html`
> Archived: 2026-10-21 · R2026b · Since R2022b · Chinese version: `zh/17-lut-based-pmsm-control-reference.md`
> Library: Motor Control Blockset / Control / Synchronous Machine / Control Reference

---

## Description

Generate lookup-table-based control reference currents for field-oriented control of permanent magnet
synchronous motor.

The LUT-Based PMSM Control Reference block generates the *d*-axis and *q*-axis reference currents for
field-oriented control and field-weakening control of a permanent magnet synchronous motor (PMSM). You can
specify reference torque and feedback mechanical speed and the block outputs the corresponding reference
current values. The block also supports the maximum torque per ampere (MTPA) and maximum torque per voltage
(MTPV) operating regions.

The block uses *id(T,ω)* and *iq(T,ω)* lookup tables (LUTs) to generate reference current values. Depending
on the input method you use to specify the motor parameters, the block can either generate LUTs or use the
data you provide.

### Motor parameter input method

You can use the **Motor parameter input method** parameter to specify one of these options:

**1. `Linear model with lumped parameters`** — The block uses lumped parameters with *Ld*, *Lq*, and *FluxPM*.

This option uses the lumped parameters to compute the *id* and *iq* LUTs. The block obtains *id* and *iq*
for the given *ω* and *T* inputs by solving the equations associated with these curves:

```
MTPA curve (IPMSM):   id² + id·ψm·(Ld − Lq) = iq²
MTPA line (SPMSM):    id = 0
Constant torque:      iq = T / (1.5·Pp·(ψm + (Ld − Lq)·id))
Current limit:        id² + iq² = imax²
Voltage limit:        (Vdc/√3)² = (id·Rs − ωe·Lq·iq)² + (iq·Rs + ωe·Ld·id + ωe·ψm)²
```

- When the motor is operating within the voltage constraints, the block solves for the intersection of
  the MTPA line and the constant torque trajectory.
- When the motor is operating beyond the voltage constraints, the block solves for the intersection of the
  voltage constraint curve and the constant torque trajectory.

After computing the *id* and *iq* tables from a grid of *ω* and *T* values, the block uses interpolation to
find *idref* and *iqref* for any *ω* and *T* inputs that lie within the range of the table values. The table
values are clipped for *ω* and *T* values beyond the boundaries.

**2. `Non-linear model with Ld, Lq, and FluxPM LUTs`** — The block uses a nonlinear model with *d*-axis and
*q*-axis stator winding inductances and permanent magnet flux linkage lookup tables.

This option uses an approach similar to the lumped parameters method, except that the block updates the
values for *Ld(id,iq)*, *Lq(id,iq)*, and *FluxPM(id,iq)* each time it computes *id* and *iq*. The block
iterates these computations until the *id* and *iq* values converge.

**3. `Non-linear model with D,Q-flux linkage LUTs`** — The block uses a nonlinear model with *d*-axis and
*q*-axis flux linkage lookup tables.

This option uses an approach similar to the lumped parameters method, except that the block updates the
values for *ψd(id,iq)* and *ψq(id,iq)* each time it computes *id* and *iq*. The block iterates these
computations until the *id* and *iq* values converge.

**4. `Non-linear model with id and iq LUTs`** — Use this option when you want to manually provide the
*id(T,ω)* and *iq(T,ω)* tables. Typically, you obtain these tables through simulations or dyno tests.

You can also generate these tables using the `mcb.generateMotorLUT` function in Motor Control Blockset™.

> **Errata note**: the "Voltage limit" equation appears as `(VDC/3)² = ...` on the English site and
> `(VDC·√3)² = ...` on the Chinese site. Cross-checking with `mtpacontrolreference` (`vmax = vdc/√3`), the
> correct form is **(Vdc/√3)² = ...** (i.e. Vdc²/3). The archive presents the corrected form.

### Vdc Input Method × Technique

| Motor parameter input method | Vdc input method | Technique |
|---|---|---|
| Linear lumped | Specify via dialog | 2D id/iq table from fixed Vdc, interpolate for references |
| Linear lumped | Input port – 3D LUT (voltage slice) | 3D table with voltage slices, select slice by Vdc port |
| Linear lumped | Input port – 2D LUT (scaled-ω) | 2D table from fixed Vdc, scale ω when Vdc port varies |
| Non-linear DQ-flux / Ldq-FluxPM / id-iq LUTs | Specify via dialog | Corresponding LUT + fixed Vdc |
| same | Input port – 3D LUT | 3D LUT sliced by voltage |
| same | Input port – 2D LUT | 2D LUT scaled by ω |

In addition, you can use the **Vdc input method** parameter to configure the block to accept a fixed
reference DC voltage through the **DC voltage to compute LUTs (V)** parameter or a variable reference DC
voltage through a separate input port **Vdc**.

For a detailed set of equations and assumptions that Motor Control Blockset uses for a PMSM, see
*Mathematical Model of PMSM*.

---

## Examples

- **PMSM Drive Characteristics and Constraint Curves**
- **Field-Weakening Control (with MTPA) of Nonlinear PMSM Using Lookup Table**

---

## Ports

| Port | Direction | Description |
|---|---|---|
| **Tref** | Input | Reference torque (Nm) |
| **⍵m** | Input | Mechanical speed (rad/s) |
| **Vdc** | Input | Variable DC bus voltage (V). Enabled when Vdc input method = Input port |
| **Idref** | Output | Reference d-axis current (A) |
| **Iqref** | Output | Reference q-axis current (A) |

Data Types: all `single` | `double` | `fixed point`

---

## Parameters

### Motor Parameters

| Parameter | Default | Description |
|---|---|---|
| **Motor topology** | `Interior PMSM` | PMSM type (interior / surface) |
| **Field weakening control method** | `CVCP` | FWC method: `CVCP` / `CCCP` / `VCLMT` / `NONE`. First three are SPMSM-only; IPMSM uses VCLMT |
| **Number of pole pairs** | `4` | Number of pole pairs |
| **Stator resistance per phase, Rs (Ohm)** | `0.36` | Stator phase resistance |
| **Vdc input method** | `Specify via dialog` | See the technique table above |
| **DC voltage to compute LUTs (V)** | `24` | DC bus voltage (when specified via dialog) |
| **DC bus voltage breakpoint vector, Vdc (V)** | `[18,30]` | Voltage breakpoints for 3D tables |
| **Motor parameter input method** | `Linear model with lumped parameters` | See the four methods above |
| **Enable percentages for torque breakpoint vector** | `off` | Define torque breakpoints in percent |
| **Enable custom breakpoint vectors for torque and speed** | `off` | Custom torque/speed lookup vectors |
| **Reference percentage torque breakpoint vector, Trefpct (%)** | `[0,50,100]` | Percentage torque breakpoints |
| **Torque envelope for speed breakpoint vector, wrpm (rpm)** | `[0.3 0.3 0.15 0.05]` | Torque envelope at speed breakpoints |
| **Reference torque breakpoint vector, Tref (Nm)** | `[0,0.15,0.3]` | Torque breakpoints (Nm) |
| **Mechanical speed breakpoint vector, wrpm (rpm)** | `[0,1000,2000,6000]` | Speed breakpoints (rpm) |
| **Current Limit, I_limit (A)** | `7.1` | Maximum phase current limit |
| **Viscous damping coefficient, Bv (Nm-s/rad)** | `2.636875217824e-6` | Viscous damping coefficient |

### Non-linear LUT Parameters (enabled per input method)

| Parameter | Description |
|---|---|
| **D-axis current breakpoint vector, id (A)** | `[-40,-20,0,20]`, d-axis current vector for Ld/Lq/FluxPM tables |
| **Q-axis current breakpoint vector, iq (A)** | `[-40,-20,0,20,40]`, same for q-axis |
| **Use measured (instead of computed) torque** | `off`, provide measured torque LUT data |
| **Measured torque LUT, T(id,iq) (Nm)** | Measured torque table |
| **Stator d-axis inductance, Ld (H)** | Ld for linear method |
| **Stator q-axis inductance, Lq (H)** | Lq for linear method |
| **Permanent magnet flux linkage (Wb)** | λpm for linear method |
| **D-axis flux linkage LUT, FluxD (id,iq) (Wb)** | For DQ-flux method |
| **Q-axis flux linkage LUT, FluxQ (id,iq) (Wb)** | For DQ-flux method |
| **Ld LUT / Lq LUT / PM flux linkage LUT (id,iq)** | For Ld/Lq/FluxPM method |
| **Reference id/iq LUT, id(Tref,wrpm[,Vdc]) (A)** | For id/iq method: 2D *id(T,ω)* or 3D *id(T,ω,Vdc)* |

### Input Units

| Parameter | Default | Description |
|---|---|---|
| **Input units** | `Per-Unit (PU)` | Block input unit system |
| **Base voltage (V)** | `24/sqrt(3)` | Per-unit base voltage |
| **Base current (A)** | `19.3` | Per-unit base current |
| **Base speed (rpm)** | `4107` | Per-unit base speed |
| **Base torque (Nm)** | `0.74112` | Per-unit base torque (computed internally, read-only) |
| **Allow scaled-down motor parameters with CodeGen** | `on` | Scale internal parameters per-unit for fixed-point precision; turn off to convert to SI at run time so tables can be swapped |

### Plotting Options

Enabled when parameter input method is Linear lumped / DQ-flux / Ldq-FluxPM and Vdc is Specify via dialog.

- **Enable saving the computed LUTs** — save the LUTs computed by the block
- **Compute (and plot) id and iq LUTs** (button)
- **Use default options for plotting** / **Motor speed (RPM)** / **Motor torque (Nm)**
- **Enable plotting the drive characteristics** / **Include the drive characteristics for an increased motor current**
- **Plot constraint curves** (button)
- **Compute and show** (button) — rated torque, rated speed, maximum speed

See *Plot Constraint Curves and Drive Characteristics for PMSM and SynRM Directly from Block Parameters
Dialog Box*.

---

## Extended Capabilities

- **C/C++ Code Generation** — Generate C and C++ code using Simulink® Coder™
- **Fixed-Point Conversion** — Design and simulate fixed-point systems using Fixed-Point Designer™

## Version History

Introduced in R2022b

## See Also

- **Blocks:** PMSM FeedForward Control | PMSM Torque Estimator | LUT based SynRM Control Reference |
  LUT based ACIM Control Reference
- **Functions:** `mcb.generateMotorLUT`
