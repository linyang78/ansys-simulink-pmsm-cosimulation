# Gain Calculation and Tuning

> **MatheWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/gain-calculation-and-tuning.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/14-gain-calculation-and-tuning.md`
> Note: This page is a category/index page. Official text below; tables are the official index entries.

---

## Overview

Motor Control Blockset helps you to select and adjusting the controller gains (PI gains) for the current,
speed, and position loops. The gains are initially calculated from the motor's electrical parameters
(resistance, inductance, inertia) and the desired bandwidth or response time of each control loop.

**In FOC, the current loops (d- and q-axis) are tuned first** because they must be fast and well-damped to
ensure proper torque and flux control. The speed loop gains are then tuned to be slower than the current
loops, ensuring stable cascaded control.

Proper gain calculation and tuning are critical to avoid oscillations, excessive torque ripple, slow
response, or even instability in the drive.

---

## Functions

| Function | Purpose |
|---|---|
| `mcb.getPIControllerParameters` | Compute gains for PI controller in field-oriented control |
| `mcb.calcFOCGains` | Compute gains and transfer functions for PI controller in FOC of PMSM (Since R2025a) |

---

## Blocks

### Controls / Controllers

| Block | Description |
|---|---|
| **PI Controller** | Discrete-time PID controller |
| **Discrete-time PID Controller** | (Since R2022a) |
| **Field Oriented Control Autotuner** | Automatically and sequentially tune multiple PID control loops in FOC application |
| **FOC Default Controller Gains** | Compute controller gains for the FOC based algorithms at run time based on empirical method or optimum theory (Since R2023b) |

### Sensorless Estimators

| Block | Description |
|---|---|
| **Sliding Mode Observer** | Compute electrical position and mechanical speed of a surface-mount PMSM |
| **Flux Observer** | Compute electrical position, magnetic flux, and electrical torque of rotor |
| **Pulsating High Freq Observer** | Estimate initial rotor electrical position of interior PMSM using pulsating high frequency (PHF) injection (Since R2022b) |
| **Extended EMF Observer** | Compute electrical position and mechanical speed of PMSM (Since R2023a) |

### Signal Management

| Block | Description |
|---|---|
| **PLL with Feed Forward** | Compute position and angular frequency from orthogonal sinusoidal signals (Since R2023b) |
| **Compute Parameter** | Extend functionality of blocks by enabling additional inputs (Since R2024a) |

---

## Topics

- **Estimate Control Gains and Tune Control Parameters** — Perform control parameter tuning for speed and
  torque control subsystems.
- **Obtain Controller Gains to Run Motor Using Field-Oriented Control** — This example shows how to obtain
  PI controller gains using Optimum theory for the current control loop and speed control loop in FOC of a PMSM.

---

## Featured Examples

| Example | Description |
|---|---|
| **Tune PI Controllers Using Field Oriented Control Autotuner** | Computes the gain values of PI controllers available in the speed and current control loops by using the Field Oriented Control Autotuner block |
| **Tune PI Controllers (in Field-Weakening Control Mode) Using FOC Autotuner Block** | Uses the FOC Autotuner block to compute the gain values of the PI controllers available in the speed, current, and **flux control loops** of a field-weakening control algorithm |
| **Tune PI Controllers Using Field Oriented Control Autotuner Block on Real-Time Systems** | Compute the gain values of PI controllers within the speed and current controllers on real-time systems |
