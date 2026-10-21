# Estimate Control Gains and Tune Control Parameters

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/gs/estimate-control-gains-from-motor-parameters.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/15-estimate-control-gains-and-tune.md`
> Note: This is the full example page referenced by *Gain Calculation and Tuning*.

---

## Overview

Tune speed and torque control loops that are part of the Field-Oriented Control (FOC) algorithm. You can
choose from these methods to compute the control loop gains from the system or block transfer functions that
are available for the motors, inverter, and controller:

- Use the Field Oriented Control Autotuner block.
- Use the FOC Default Controller Gains block.
- Use Simulink® Control Design™.
- Use the model initialization script.

To compute control loop gains, each method requires the following control parameters:

- Motor, inverter, and target parameters
- Control execution time
- Delays and per-unit system values

---

## Four Methods

### 1. Field-Oriented Control Autotuner Block

The Field-Oriented Control Autotuner block of Motor Control Blockset™ enables you to automatically tune the PID
control loops in your Field-Oriented Control (FOC) application in real time. You can automatically tune the PID
controllers associated with the following loops:

- Direct-axis (*d*-axis) current loop
- Quadrature-axis (*q*-axis) current loop
- Speed loop

For each loop that the block tunes, the Field-Oriented Control Autotuner block performs autotuning experiment in
a closed-loop manner without using a parametric model associated with that loop. The block enables you to
specify the order in which the block tunes the control loops. When the tuning experiment runs for one loop, the
block has no effect on the other loops.

### 2. FOC Default Controller Gains Block

The FOC Default Controller Gains block of Motor Control Blockset enables you to integrate control gain
calculations into the controller code. Using the library block, you can determine controller gains during
runtime without recompiling the code when switching between different motor setups.

### 3. Simulink Control Design

Simulink Control Design enables you to design and analyze the control systems modeled in Simulink. You can
automatically tune the arbitrary single-input, single-output (SISO) and multiple-input, multiple-output (MIMO)
control architectures, including the PID controllers. You can deploy PID autotuning to the embedded software to
automatically compute the PID gains in real time.

You can find the operating points and compute the exact linearizations of the Simulink models at different
operating conditions. Simulink Control Design provides tools that let you compute the simulation-based
frequency responses without modifying your model.

### 4. Model Initialization Script

You can use the initialization scripts included with Motor Control Blockset examples to initialize the control
parameters needed to estimate control gains.

For example, for a PMSM that is connected to a quadrature encoder, these steps describe the procedure to
initialize control parameters from the system details by using the initialization script:

1. Open an example that uses an initialization script. For instance:

   ```matlab
   openExample('mcb/FOCQepExample')
   ```

2. Open the initialization script (`.m`) file of the example in MATLAB®. To find the associated script file name:
   1. Open the example model. Select **Modeling > Model Settings > Model Properties**.
   2. In the Model Properties dialog box, navigate to the **Callbacks** tab > **InitFcn** field. This field
      contains the name of the script that Simulink executes at the beginning of model compilation.
3. Use the **Workspace** to edit the control variables values. For example, to update stator resistance
   (`Rs`), use the variable `pmsm` to add the parameter value to the `Rs` field.

---

## Initialize Control Parameters

The model initialization script associated with the target model calls the following functions and sets up the
workspace with the required variables.

| Function | Description |
|---|---|
| `mcb.getPMSMParameters` | Input is make/manufacturer (e.g. BLY171D). Returns the `pmsm` structure; computes PM flux linkage and rated torque; automatically loads `motorParam` from parameter estimation if present in the workspace |
| `mcb.getACIMParameters` | ACIM equivalent (e.g. EM_Synergy) |
| `mcb.getInverterParameters` | Input is inverter make/model (e.g. BoostXL-DRV8305). Returns the `inverter` structure; computes inverter resistance |
| `mcb.getProcessorParameters` | Input is processor model and PWM switching frequency. Returns the `target` structure; computes ePWM counter period |
| `mcb.getPUSystemParameters` | Sets per-unit base values for voltage/current/speed/torque/power; returns `PU_System` |
| `mcb.getSISystemParameters` | SI-system base values; returns `SI_System` |
| `mcb.updateInverterParameters` | Updates inverter parameters for the selected hardware and motor |

> **Note:** For predefined processors and drivers, the model initialization script uses the default values.

---

## Compute Control Gains

| Quantity | Function | Purpose |
|---|---|---|
| Motor base speed | `mcb.getMotorBaseSpeed` | Computes base speed of the PMSM at rated voltage and rated load (max speed outside field-weakening region) |
| Motor characteristics | `mcb.PMSMCharacteristics` | Torque-speed, power-speed, Idq-speed, max phase current-speed characteristics |
| ACIM characteristics | `mcb.ACIMCharacteristics` | Induction machine version |
| PI gains (legacy) | `mcb.getPIControllerParameters` | Computes Kp/Ki for Id/Iq current loops, speed loop, **and field-weakening loop** |
| PI gains (new, R2025a+) | `mcb.calcFOCGains` | Computes FOC PI controller gains and transfer functions for a PMSM |
| Frequency-domain analysis | `mcb.getMotorControlAnalysis` | Frequency-domain analysis of the computed PI gains (requires Control System Toolbox™) |

To compute PI controller gains for a PMSM, use `mcb.calcFOCGains` instead.

---

## See Also

- Field-Oriented Control of PMSM Using Quadrature Encoder
- Obtain Controller Gains to Run Motor Using Field-Oriented Control
- PMSM Constraint Curves and Their Application
