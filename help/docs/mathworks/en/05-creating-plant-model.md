# Creating Plant Model Using Motor Control Blockset

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ug/creating-plant-model.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/05-creating-plant-model.md`
> Note: Official text transcribed paragraph by paragraph. Code blocks and paths are as in the original.

---

## Overview

An accurate plant model is a vital part of motor control system development. After creating an accurate plant
model, you can verify the functionality of the control system, conduct closed-loop model-in-the-loop tests,
tune the controller gains using simulation, and optimize the algorithm before you deploy the model in the
actual plant.

When you create a plant model using Motor Control Blockset™, you model these components to simulate the
functional behavior in a simulation environment:

- Permanent Magnet Synchronous Motor (PMSM)
- Average-value Inverter
- Sensors and signal conditioning circuits
- Processor peripherals: Analog-to-Digital converter (ADC) and Pulse-width-modulator (PWM)

You can verify the functionality of the plant model you create by:

1. Reading the normalized PWM duty cycle from the control algorithm.
2. Simulating the motor for the connected load.
3. Obtaining the output motor phase current (in terms of ADC counts) and the output motor position (in terms
   of encoder pulse counts) from the simulation.

---

## Workflow (6 Steps)

The workflow to create a plant model involves these steps.

> **Note:** See the plant model in the `mcb_pmsm_foc_qep_f28379d.slx` model that is used in the example
> *Field-Oriented Control of PMSM Using Quadrature Encoder*.

| Step | Topic | Path |
|---|---|---|
| 1 | Use PMSM Block and Motor Parameters to Design Plant Model | `ug/use-pmsm-estimated-parameters-design-model.html` |
| 2 | Add Average-Value Inverter Block | `ug/add-average-inverter-modeling.html` |
| 3 | Create Motor Phase Current Sensing and Signal Conditioning Subsystem | `ug/create-motor-phase-current-sensing-algorithm.html` |
| 4 | Create Position Sensing Subsystem | `ug/create-positioning-sensing-subsystem.html` |
| 5 | Add Delay in Plant Model | `ug/add-delay-plantmoodeling.html` |
| 6 | Integrate Blocks and Subsystems | `ug/integrate-blocks-and-subsystems-plantmodeling.html` |

---

## See Also

- Estimate PMSM Parameters Using Parameter Estimation Blocks
- Design Field-Oriented Control Algorithm
- Field-Oriented Control of PMSM Using Quadrature Encoder
