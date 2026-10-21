# Field-Oriented Control of PMSM Using Quadrature Encoder

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/gs/foc-pmsm-using-quadrature-encoder.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/10-foc-pmsm-using-quadrature-encoder.md`
> Note: This is the benchmark FOC example of Motor Control Blockset — quadrature encoder, outer speed loop +
> inner current loops, deployable to TI C2000 hardware.

---

## Overview

This example implements the field-oriented control (FOC) technique to control the speed of a three-phase
permanent magnet synchronous motor (PMSM). The FOC algorithm requires rotor position feedback, which is obtained
by a quadrature encoder sensor. For details about FOC, see *Field-Oriented Control*.

This example uses the quadrature encoder sensor to measure the rotor position. The quadrature encoder sensor
consists of a disk with two tracks or channels that are coded 90 electrical degrees out of phase. This creates
two pulses (A and B) that have a phase difference of 90 degrees and an index pulse (I). Therefore, the
controller uses the phase relationship between A and B channels and the transition of channel states to
determine the direction of rotation of the motor.

---

## Models

The example includes these models:

| Model | Hardware |
|---|---|
| `mcb_pmsm_foc_qep_f28069m` | F28069M control card + DRV8312-69M-KIT inverter |
| `mcb_pmsm_foc_qep_f28069LaunchPad` | LAUNCHXL-F28069M + BOOSTXL-DRV8305 |
| `mcb_pmsm_foc_system` | System-level simulation model (LaunchPad configuration) |
| `mcb_pmsm_foc_qep_f28379d` | LAUNCHXL-F28379D + BOOSTXL-DRV8305 / BOOSTXL-3PHGANINV |

You can use these models for both simulation and code generation.

---

## Required MathWorks Products

**To simulate model:**

| Model | Products |
|---|---|
| `mcb_pmsm_foc_qep_f28069m` / `..._f28069LaunchPad` / `mcb_pmsm_foc_system` | Motor Control Blockset™ + Fixed-Point Designer™ |
| `mcb_pmsm_foc_qep_f28379d` | Motor Control Blockset |

**To generate code and deploy model:**

| Model | Products |
|---|---|
| the three F28069M models above | Motor Control Blockset + Embedded Coder® + C2000™ Microcontroller Blockset + Fixed-Point Designer™ |
| `mcb_pmsm_foc_qep_f28379d` | Motor Control Blockset + Embedded Coder® + C2000™ Microcontroller Blockset + Fixed-Point Designer™ (only needed for optimized code generation) |

---

## Prerequisites

1. Obtain the motor parameters. We provide default motor parameters with the Simulink® model that you can
   replace with the values from either the motor datasheet or other sources.

   However, if you have the motor control hardware, you can estimate the parameters for the motor that you want
   to use, by using the Motor Control Blockset parameter estimation tool. For instructions, see *Estimate Motor
   Parameters Using Motor Control Blockset Parameter Estimation Tool*.

   The parameter estimation tool updates the *motorParam* variable (in the MATLAB® workspace) with the
   estimated motor parameters.

2. If you obtain the motor parameters from the datasheet or other sources, update the motor parameters and
   inverter parameters in the model initialization script associated with the Simulink® models. For
   instructions, see *Estimate Control Gains and Tune Control Parameters*.

   If you use the parameter estimation tool, you can update the inverter parameters, but do not update the
   motor parameters in the model initialization script. The script automatically extracts motor parameters from
   the updated *motorParam* workspace variable.

---

## Simulate Model

This example supports simulation. Follow these steps to simulate the model.

1. Open a model included with this example.
2. Click **Run** on the **Simulation** tab to simulate the model.
3. Click **Data Inspector** on the **Simulation** tab to view and analyze the simulation results.

---

## Generate Code and Run on Target Hardware

This example uses a host and a target model. The host model is a user interface to the controller hardware
board. You can run the host model on the host computer. The prerequisite to use the host model is to deploy the
target model to the controller hardware board. The host model uses serial communication to command the target
Simulink® model and run the motor in a closed-loop control.

**Required Hardware:**

- F28069M control card + DRV8312-69M-KIT inverter: `mcb_pmsm_foc_qep_f28069m`
- LAUNCHXL-F28069M controller + BOOSTXL-DRV8305 inverter: `mcb_pmsm_foc_qep_f28069LaunchPad` and
  `mcb_pmsm_foc_system`
- LAUNCHXL-F28379D controller + (BOOSTXL-DRV8305 or BOOSTXL-3PHGANINV) inverter: `mcb_pmsm_foc_qep_f28379d`

> **NOTE:** When using the BOOSTXL-3PHGANINV inverter, ensure that proper insulation is available between the
> bottom layer of BOOSTXL-3PHGANINV and the LAUNCHXL board.

**Steps:**

1. Simulate the target model and observe the results.
2. Complete the hardware connections.
3. The model automatically computes the ADC (or current) offset values. To disable (enabled by default), set
   `inverter.ADCOffsetCalibEnable` to 0 in the initialization script. You can also compute the ADC offset
   manually and write it into the script (see *Run 3-Phase AC Motors in Open-Loop Control and Calibrate ADC
   Offset*).
4. Compute the quadrature encoder index offset value and write it into the target model initialization script
   (see *Quadrature Encoder Offset Calibration for PMSM*).
5. Verify the encoder slit count: check and update `pmsm.QEPSlits` in the initialization script (corresponds to
   the **Encoder slits** parameter of the Quadrature Decoder block; see *Quadrature Decoder* for **Encoder
   slits** and **Encoder counts per slit**).
6. Open the target model for the required hardware configuration (see *Model Configuration Parameters* to
   change default settings).
7. Load a sample program (e.g. `c28379D_cpu2_blink.slx`, blinking GPIO31) to CPU2 of the LAUNCHXL-F28379D, so
   that CPU2 is not mistakenly configured to use board peripherals reserved for CPU1.
8. Click **Build, Deploy & Start** on the **Hardware** tab to deploy the target model.
9. Click the `mcb_host_model_f28069m.slx` host model hyperlink in the target model to open the host model.
10. Specify the communication port with the variable `target.comport` (updates the Port parameter of Host
    Serial Setup / Receive / Transmit).
11. Update the Reference Speed value in the host model.
12. Click **Run** on the **Simulation** tab to run the host model.
13. Change the Start / Stop Motor switch to On to start running the motor.
14. Observe the debug signals from the RX subsystem in the host model's Time Scope.

> **Note:** If you are using an F28379D-based controller, you can also select which debug signals to monitor.

---

## Cross References

- FOC principles → `01-field-oriented-control.md`
- Five-step controller workflow → `07-design-field-oriented-control-algorithm.md` +
  `08-design-current-controller.md`
- Plant model → `05-creating-plant-model.md`
- Parameters → `13-estimate-pmsm-parameters.md`
- Gains → `15-estimate-control-gains-and-tune.md`, `14-gain-calculation-and-tuning.md`
- Open-loop startup / ADC / encoder calibration are referenced in steps 3 and 4 above
