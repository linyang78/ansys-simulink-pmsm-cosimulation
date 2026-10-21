# Design Field-Oriented Control Algorithm

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/ug/design-field-oriented-control-algorithm.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/07-design-field-oriented-control-algorithm.md`
> Note: This is the **overview page** of the five-step FOC design workflow (R2026b; earlier releases had four
> steps — a current/position scaling step was added). Each step has its own detail page.

---

## Overview

To implement the speed control algorithm for a motor, perform these tasks:

- **Current scaling** — Convert current from ADC counts to PU.
- **Quadrature encoder position decoding** — Read the quadrature encoder position counts and calculate the
  rotor electrical position.
- **Torque control** — Implement current control in the *d*-*q* axis.
- **Speed control** — Implement speed control.

These steps help you implement the speed control algorithm for a PMSM using Motor Control Blockset™ and are
related to the model `mcb_pmsm_foc_qep_f28379d` used in the example *Field-Oriented Control of PMSM Using
Quadrature Encoder*. They explain the procedure to tune the control parameters for *d*-axis and *q*-axis
current controllers and the speed controller.

---

## 5-Step Workflow

| Step | Page | Content |
|---|---|---|
| 1 | Design Current and Position Scaling Subsystems | Current/position scaling to per-unit (ADC counts → PU) |
| 2 | Design Current Controller Subsystem | Current controller (PI + Clarke/Park + PWM generation) |
| 3 | Perform Manual Gain-Tuning of Current Controller | Manual gain tuning of the current controller |
| 4 | Design Speed Control Algorithm | Speed control algorithm (outer loop) |
| 5 | Perform Manual Gain-Tuning of Speed Controller | Manual gain tuning of the speed controller |

In these steps, variables are used to define datatypes and execution times of the current and speed
controllers. See the initialization script linked to the example model `mcb_pmsm_foc_qep_f28379d` for details
about the variables defined in these steps.

> **Tip:** A basic understanding of Simulink® is a prerequisite for following this workflow, as these workflow
> steps do not provide details on tasks like defining a datatype in a constant block or using math operations
> blocks in Simulink.

See *Estimate PMSM Parameters Using Parameter Estimation Blocks* for estimating the motor parameters. Then, see
*Creating Plant Model Using Motor Control Blockset* to design a plant model. This helps you verify the control
algorithm in simulation.

---

## Reading Order Across This Archive

```
1. 13-estimate-pmsm-parameters      Obtain motor parameters (Rs/Ld/Lq/Ke/J/B)
2. 05-creating-plant-model          Build the plant (motor + inverter + sensing + delays)
3. this page                        Build the controller (scaling → current loop → speed loop)
4. 08-design-current-controller     Detail expansion of step 2
5. 15-estimate-control-gains-and-tune   Compute PI gains (mcb.getPIControllerParameters etc.)
6. 09-field-oriented-current-controller  Ready-made current controller block reference
```

## See Also

- Design Current Controller Subsystem
- Design Speed Control Algorithm
- Field-Oriented Control of PMSM Using Quadrature Encoder
