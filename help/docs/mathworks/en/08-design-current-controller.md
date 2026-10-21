# Design Current Controller Subsystem

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ug/design-current-controller.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/08-design-current-controller.md`
> Position: Step 2 of the 5-step FOC design workflow.
> Note: This page has no official Chinese translation; the Chinese archive is an editor's translation.

---

## Steps

Use these steps to design the current controller subsystem:

**Step 1.** From the Motor Control Blockset™ library in the Simulink® Library Browser, use the
**PI Controller** block (in the Controls/Controllers library) to design the *d*-axis and *q*-axis current
control. For example, this image shows the *d*-axis current controller subsystem.

The MATLAB® function `mcb.getPIControllerParameters` (in the model initialization script) calculates the PI
control gains for the *d*-axis and *q*-axis current controller and the speed controller. For details about
calculation of the controller gains, see *Estimate Control Gains and Tune Control Parameters*. For example, see
the model initialization script file `mcb_pmsm_foc_qep_f28379d_data.m` (used in the example *Field-Oriented
Control of PMSM Using Quadrature Encoder*) that uses a sampling time (*Ts*) of `50` μs.

In the subsystem diagram, the *Enable* variable is a Data Store Memory used to reset the controller. Adding
*Enable* variable is optional.

The subsystem also uses three constant blocks with these values:

- `PI_params.Kp_i`
- `Ki_i*Ts`
- `0`

Create a similar subsystem for the *q*-axis current PI controller. Integrate the subsystems for *d*-axis and
*q*-axis PI controllers into a single subsystem (Current_Controllers) that controls the *d*-axis and *q*-axis
currents.

**Step 2.** Add the **Clarke Transform**, **Park Transform**, **Inverse Park Transform**, and **PWM Reference
Generator** blocks from the `Motor Control Blockset/Controls/Math Transforms` library to the Current_Controllers
subsystem (that you created in step 1).

**Step 3.** Integrate the components that you created in step 2 into a single subsystem (Closed Loop Control
that implements closed loop field-oriented control).

**Step 4.** Create an **Output Scaling** subsystem to scale the Pulse Width Modulation (PWM) outputs. This
subsystem outputs the normalized PWM duty cycles (`0`–`1`) for the plant model.

**Step 5.** Create a new subsystem by integrating the current scaling (Calculate Phase Currents), QEP position
decoding (Calculate Position and Speed), Closed Loop Control, and Output Scaling subsystems. Add the **Trigger**
block from the `Simulink/Ports & Subsystems` library to this subsystem and set the **Trigger type** parameter to
`function-call`.

**Step 6.** Add a **Function-Call Generator** block from the `Simulink/Ports & Subsystems` library to the
subsystem created in step 5. Set the **Sample time** parameter of the block to equal to the control-loop sample
time, *Ts* (that has a default value of `50e-6` s).

**Step 7.** Integrate the plant model and the controller subsystem that you created in step 6. For detailed
steps on how to create a plant model for a motor control system, see *Creating Plant Model Using Motor Control
Blockset*.

> [Figures: subsystem diagrams — antiwindup, all_transforms, closedloop, outputscaling, withtrigger,
> integrate1, integrate2]

---

## Key Takeaways

- **Two PI loops** — one PI controller each for *d* and *q* axis; inputs are the difference between reference
  and measured d-q currents; outputs are the *d-q* reference voltages.
- **Four transforms** — Clarke (ia,ib → αβ), Park (αβ → dq), Inverse Park (dq → αβ), PWM Reference Generator
  (→ duty cycles).
- **Triggered execution** — Trigger + Function-Call Generator fixes the control-loop period (example: 50 μs,
  i.e. 20 kHz current loop).
- **Anti-windup** — visible in the diagrams; the MCB PI Controller block has integral clamping via PIConfig.
- **Enable reset** — used to reset PI integrators at open-loop → closed-loop transition or on faults.

---

## See Also

- Previous step: Design Current and Position Scaling Subsystems
- Next step: Current Controller Manual Gains
- Overview: Design Field-Oriented Control Algorithm
- Equivalent ready-made block: Field-Oriented Current Controller
