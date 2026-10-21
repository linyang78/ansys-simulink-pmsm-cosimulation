# Estimate PMSM Parameters Using Parameter Estimation Blocks

> **MathWorks official document archive (English)**
> Source: `https://www.mathworks.com/help/mcb/gs/pmsm-parameter-estimation-using-recommended-hardware.html`
> Archived: 2026-10-21 · R2026b · Chinese version: `zh/13-estimate-pmsm-parameters.md`
> Note: The original page is long; this archive keeps all sections and key steps.

---

## Overview

This example uses the parameter estimation blocks provided by Motor Control Blockset™ to estimate these
parameters of a permanent magnet synchronous motor (PMSM) with a quadrature encoder sensor:

- Phase resistance, *Rs* (Ohm)
- D-axis inductance, *Ld* (Henry)
- Q-axis inductance, *Lq* (Henry)
- Back-EMF constant, *Ke* (Vpk_LL/krpm, where Vpk_LL is the peak voltage line-to-line measurement)
- Motor inertia, *J* (Kg·m²)
- Friction constant, *B* (N·m·s)

For an example that covers sensorless parameter estimation, see *Generate Motor Control Models for Selected
Algorithm and Hardware*.

Motor parameter estimation is vital for implementing motor control algorithms accurately. Accurate motor
parameters enable the algorithm to compute the control parameters with precision. Therefore, an accurate
representation of motor parameters is necessary for a finer speed and torque control when you run PMSMs using
control techniques such as field-oriented control (FOC). Motor parameter estimation also enables you to verify
the parameter values provided by the motor datasheet. In addition, it enables you to accurately replicate the
plant model in Simulink® using which you can simulate real-world scenarios and tests that are difficult to
execute using a physical hardware setup.

Accurate simulation helps you reconfigure and run these tests multiple times, which can be difficult when you
use physical hardware. Therefore, these exhaustive tests enable you to predict, find, and fix problems with
ease including failures that are hard-to-reproduce.

The example shows you how to use these blocks to design and implement a PMSM parameter estimation algorithm on
a Texas Instruments® hardware board:

- PMSM Parameter Estimation Configurator
- PMSM Rs Estimator
- Ld Estimator
- Lq Estimator
- PMSM Mechanical Parameter Estimation

Alternatively, using this example as a reference, you can utilize these blocks to implement a similar algorithm
on a different hardware board or configuration.

---

## Model

The target model included in the example uses the parameter estimation blocks in the
`mcb_pmsm_param_est_f28379d/Parameter Estimation/Param Est` subsystem.

These subsystems use the parameter estimation blocks to estimate *Rs*, *Ld*, *Lq*, and the mechanical
parameters:

- `RsTest` — Uses the Rs Estimator block to estimate the motor resistance.
- `LdTest` — Uses the Ld Estimator block to estimate *d*-axis inductance.
- `LqTest` — Uses the Lq Estimator block to estimate *q*-axis inductance.
- `MechParam` — Uses the PMSM Mechanical Parameter Estimation block to estimate the back-EMF constant, motor
  inertia, and the friction constant.

If you are only simulating the example, the target model displays the estimated parameters. When you deploy the
target model to the hardware, use the host model to estimate the parameters using the hardware.

**Model:** `mcb_pmsm_param_est_f28379d`

**Required MathWorks Products:**
- Simulation: Motor Control Blockset (Stateflow® required only if modifying the example model)
- Code generation and deployment: Motor Control Blockset, Embedded Coder®, C2000™ Microcontroller Blockset,
  Stateflow

---

## Prerequisites

Check and update the mandatory motor, inverter, and other system parameters listed in the model initialization
script `mcb_pmsm_param_est_f28379d_data.m`.

In addition, you can update the optional motor parameters for simulation.

You can use the inverter and motor hardware datasheet to determine these values.

---

## Simulate Model

1. Open the target model included with this example.
2. If required, change the configuration elements for parameter estimation, by updating the mask parameters of
   the PMSM Parameter Estimation Configurator block available in the
   `mcb_pmsm_param_est_f28379d/Serial Receive/Variant Subsystem/Sim` subsystem.
3. In the **User Controls** section, ensure that the **Parameter Estimation** switch is set to **Stop**.
4. Click **Run** on the **Simulation** tab to simulate the model.
5. Set the **Test Method** switch to either **Manual** or **Auto** mode.
   - **Manual** — execute the tests one by one in the prescribed sequence.
   - **Auto** — automatically run all the tests in the prescribed sequence.

**Manual mode:** set **Test Method** to **Manual**; use the **Test Select** button to select the first test
`Rs`; turn the **Parameter Estimation** switch to **Start**. The model runs the *Rs* estimation test after which
it displays the computed value in the **Estimated Parameters** field. Turn the switch to **Stop**. Similarly,
use the **Test Select** button to select the next test and repeat.

**Auto mode:** set **Test Method** to **Auto**; turn the **Parameter Estimation** switch to **Start**. The model
starts running all tests in the prescribed sequence of `Rs` → `Ld` → `Lq` → `(Ke, J, B)`, after which it
displays the computed parameter values in the **Estimated Parameters** field.

> **Note:** Ensure that you run all tests in the prescribed sequence of `Rs` → `Ld` → `Lq` → `(Ke, J, B)`. Do
> not skip any test.

During simulation, the target model does not support computation of *J*. In Auto mode the **Test Select**
button has no effect.

---

## Generate Code and Deploy

**Required Hardware:** LAUNCHXL-F28379D controller + BOOSTXL-DRV8305 inverter (`mcb_pmsm_param_est_f28379d`)

1. Complete the hardware connections.
2. The model automatically computes ADC (or current) offset values. To disable (enabled by default), set
   `inverter.ADCOffsetCalibEnable` to 0 in the initialization script. You can also compute the ADC offset
   manually (see *Run 3-Phase AC Motors in Open-Loop Control and Calibrate ADC Offset*).
3. Compute the quadrature encoder index offset value and write it into the target model initialization script
   (see *Quadrature Encoder Offset Calibration for PMSM*). Verify the encoder slit count and update
   `pmsm.QEPSlits` (corresponds to **Encoder slits** of the Quadrature Decoder block).
4. Open the target model (see *Model Configuration Parameters* to change hardware settings).
5. Load a sample program (e.g. `c28379D_cpu2_blink.slx`) to CPU2 of the LAUNCHXL-F28379D, so that CPU2 does
   not mistakenly use board peripherals reserved for CPU1.
6. Click **Build, Deploy & Start** on the **Hardware** tab.
7. Verify that the target model variables are available in the MATLAB base workspace.
8. Click the `mcb_pmsm_param_est_host_f28379d.slx` host model hyperlink to open the host model (serial
   communication: see *Host-Target Communication*).
9. If needed, change the mask parameters of the PMSM Parameter Estimation Configurator in the host model.
10. Specify the communication port with the variable `target.comport`.
11. In **User Controls**, set the **Parameter Estimation** switch to **Stop**.
12. Click **Run** to start communication between the host model and the target hardware.
13. Set **Test Method** to **Manual** or **Auto** (as in the simulation section). The **Active Test** field
    shows the currently running test.
14. Select signals with the **Debug Signals** dropdown and monitor them on the scope.

### Protection Faults

The model can interrupt the currently running test and turn the following LEDs red to protect the hardware:

- **Over-current fault** — occurs when the actual current drawn from the power supply is more than the
  overcurrent limit specified by the variables *motor.OverCurrLim* and *motor.I_rated* in the model
  initialization script.
- **Under-voltage fault** — occurs when input DC voltage drops below the undervoltage limit specified by the
  variables *inverter.UnderVoltLim* and *inverter.V_dc*.

The **Error Code** block displays diagnostic information about errors encountered during testing. Identify the
root cause of each error using this information along with the running (active) test and the documentation for
its parameter estimation block.

After the parameter estimation tests are complete, the host model saves the computed parameters in the
*motorParam* variable inside the base workspace.

---

## See Also

- **Apps:** Motor Hardware Configurator | Motor Parameter Estimator
- **Blocks:** PMSM Rs Estimator | Ld Estimator | Lq Estimator | PMSM Mechanical Parameter Estimator |
  PMSM Parameter Estimation Configurator
- **Topics:** Estimate PMSM Parameters Using Custom Hardware | Run-Time Parameter Estimation of PMSM Using
  Sensor Feedback | Estimate PMSM Parameters Using Parameter Estimation Blocks on Real-Time Systems |
  Estimate PMSM Parameters Using FPGA-Based Motor Control Development Kit
