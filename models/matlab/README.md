# MATLAB / Simulink side — e11 IPM control model

This folder holds the Simulink implementation of the e11 (BMW i3) IPM motor control model:
FOC + SVPWM + MTPA + field weakening, driven by Motor-CAD ECE data.

## Quick start

1. Add the folders to the MATLAB path:

```matlab
addpath('<repo>/models/matlab');
addpath('<repo>/models/matlab/nonlin-fwc');
addpath('<repo>/models/matlab/e11');
```

2. Either open the prepared model directly:

```
models/matlab/e11/e11_pmsm_nonlin_fwc.slx
```

   …or edit `mcb_e11_params.m` and run `run_e11_sim.m` for a scripted run
   (results land in `results/sim/`).

## Verified result

No-load start to 3000 rpm, 2 s simulation:

| Quantity | Value |
|---|---|
| Speed reference | 3000 rpm |
| Speed feedback | **2998.8 rpm** (error 1.2 rpm / 0.04 %) |
| Id | −338 A (field weakening active) |
| Iq | 1.7 A (no load) |
| Torque | 1.93 N m (friction only) |

> Start-up needs about 1 s: the e11 rotor inertia is **0.030 kg m²**
> (Motor-CAD measured), roughly 60× a bench motor. A 0.5 s window stops
> mid-transient and looks like a controller fault. Use `stop_time_s >= 1.5`.

## Files

### e11-specific (written for this project)

| File | Purpose |
|---|---|
| `mcb_e11_params.m` | **Single source of truth** for scenario settings |
| `mcb_e11_nonlin_setup.m` | Assembles motor parameters, LUTs and controller gains |
| `run_e11_sim.m` | Scripted run; saves to `results/sim/` |
| `e11_build_pmsmlut.m` | Builds the reference-current LUT from ECE data |
| `e11_pmsm_lut_data.mat` | Ld/Lq/FluxPM tables (91×91, secant method) |
| `e11_pmsmlut_full.mat` | Full PMSMLUT incl. id/iq reference tables |
| `e11/e11_pmsm_nonlin_fwc.slx` | Prepared model with e11 settings baked in |

### Copies of MathWorks files (required to run)

| File | Origin |
|---|---|
| `mcb_SetPMSMMotorParameters.m` | `toolbox/mcb//utils/`, extended with a `case 'e11'` entry |
| `mcb_SetInverterParameters.m` | `toolbox/mcb//utils/`, extended with a `case 'e11-inverter'` entry |
| `nonlin-fwc/*` | `FWCWithMTPAOfNonLinearPMSMUsingLUTExample` example folder |
| `mcb_ipmsm_fwc_qep_f28379d*` | `FieldWeakeningControlWithMTPAExample` example folder |

The two parameter files are **local copies on purpose**: the originals live in the
MATLAB installation and must not be edited. Adding the `models/matlab` folder to the
path shadows the built-ins with these extended versions.

## Deviations from the stock example

| Item | Stock example | Here | Why |
|---|---|---|---|
| Motor | IPMSM template (5 A) | e11 (433 A) | Target machine |
| Ld/Lq source | Constant scalars | 91×91 LUT from Motor-CAD ECE | e11 saturates hard (Lq spans 239–686 µH) |
| Inverter | BoostXL-DRV8305 (23.6 A sense) | `e11-inverter` (500 A sense) | `ISenseMax` is the per-unit current base; a 23.6 A base against a 433 A motor corrupts every PI gain |
| PU system | `mcb_SetPUSystem` | Built analytically | That helper raises `undefined function 'sqrt' for input arguments of type 'int64'` on this toolchain |
| Speed-loop gain | `Kp=2, Ki=15` hard-coded | From `mcb_SetControllerParameters` | The hard-coded pair is tuned for a 5 A bench motor |
| Speed/load reference | Knob widgets | The two `Constant` blocks | `KnobBlock` has **no output ports**; it does not drive the control path |

## Known limitations

- `mcbPMSMMaxSpeed` returns an implausible value for this machine (~200 000 rpm);
  the speed grid in the LUT is therefore set explicitly to 1–10 000 rpm.
- The speed-loop gains come from `mcb_SetControllerParameters` unchanged. They are
  validated only for the no-load 3000 rpm case above; loaded and field-weakening
  operating points are not yet tuned.
- `B` (viscous damping) is back-calculated from the 30 W friction loss at 6000 rpm
  (7.599e-05 kg m²/s). Motor-CAD reports no damping coefficient directly.
