# Ansys–Simulink PMSM Co-simulation Scripts

**English** | [中文](README.zh-CN.md)

Automation tooling for permanent magnet synchronous motor (PMSM) multi-domain co-simulation.

It chains **Motor-CAD** (rapid modeling) → **Ansys Maxwell** (finite-element solving) →
**Ansys Twin Builder** (drive circuit) → **MATLAB/Simulink** (closed-loop control)
into a scriptable pipeline for motor modeling, control-strategy validation, and fault-injection studies.

The case study threaded through this repository is the BMW i3 (e11) interior permanent magnet (IPM) motor.

---

## The problem this repository solves

In motor simulation, the time sink is rarely the FEA solve itself — it is **moving data between tools**:

| Pain point | Typical cost | What this repository does |
|---|---|---|
| Exporting an ECE equivalent circuit from Motor-CAD: a dozen manual clicks, easy to mis-enter | 20–30 min each | `dist/ece-export`, one command |
| Binding each Twin Builder machine model to Simulink through GUI dialogs | 5–10 min per model | `dist/simulink-binding`, batch binding |
| Extracting a Maxwell ECE model: placing elements in the circuit editor, configuring sweeps | 30 min+ each | `dist/maxwell-ece`, a five-step flow |

All three are **CLI tools with explicit exit codes** — no GUI clicking, so they drop straight into scripts
or into agent-driven workflows.

---

## The three tools

### 1. `dist/simulink-binding` — Twin Builder ⇄ Simulink binding

Finds `SimulinkData` components inside an `.aedt` project and generates a separate `.slx` for each,
containing one `AnsoftSFunction` block with the binding parameters written in.

```powershell
# Reconnaissance first: see how many components are available
python scripts/bind_simulink.py <project.aedt> --dry-run

# Generate
python scripts/bind_simulink.py <project.aedt> --out-dir <output-dir>
```

**Output:** `<output-dir>/<design-name>.slx` — one model per block.

**Why one model per block:** binding several blocks consecutively inside a single model reliably fails
from the second block onward (the binding dialog never appears within 60 s). With one model per block,
every case succeeded. The root cause was not identified; the shipped form follows what measured clean.

**Exit codes**

| Code | Meaning | What to do |
|---|---|---|
| 0 | All blocks bound and verified | Read `<out-dir>/*.slx` |
| 1 | Partial failure | Inspect the `FAIL` rows in the stdout result table |
| 2 | Parse failure (bad path / no components) | **Do not retry** — this is an input problem |
| 3 | Engine failure (MATLAB will not start) | Check the environment, then **retry once** |

---

### 2. `dist/ece-export` — Motor-CAD ECE equivalent circuit export

Exports the **ECE triplet** (SML / TXT / MAT) from a Motor-CAD `.mot` model, ready to import into Twin Builder,
and derives machine parameters and PI control gains from the resulting MAT file.

```powershell
# Validate the configuration first
python scripts/run_ece_export.py --config config/ece_config.json --dry-run

# Export
python scripts/run_ece_export.py --config config/ece_config.json

# Derive control parameters
python scripts/calc_control_params.py --mat <ECE_map.mat> --json-out params.json
```

**Output**

```
<output_dir>/
├── ECE_<base>_map.mat       Raw saturation map
├── ECE_<base>_txt_file.txt  Human-readable lookup table (Ψd/Ψq/Ψ0/torque)
└── ECE_<base>_sml_file.sml  ← import this one into Twin Builder
```

**⚠️ The grid must contain 0 A.** Motor-CAD requires a point at `Id = 0`.
Therefore `2 × id_max / current_step` must be even (points per axis = segments + 1 = odd),
or the run fails only after hours of solving. The script validates this locally before starting FEA.

| Segments | Points/axis | Step (±433 A) | Operating points | Measured time |
|---|---|---|---|---|
| 8 | 9 | 108.25 A | 81 | 5.2 min |
| 20 | 21 | 43.30 A | 441 | 29.5 min |
| 60 | 61 | 14.43 A | 3,721 | 243.5 min |

**Exit codes:** 0 success · 1 export failure (retryable) · 2 unusable configuration (do not retry) · 3 Motor-CAD unreachable

---

### 3. `dist/maxwell-ece` — Maxwell native ECE extraction

Combines **ECE3_Model + ECER_Model** inside Maxwell 2D to extract saturation and torque lookup tables,
producing a `.sph` netlist, an `.sml` model, and a `.txt` lookup table.

Difference from tool 2: tool 2 uses Motor-CAD's analytical model (fast); tool 3 uses the Maxwell finite-element
solution (accurate, but slow). Faulty machines and re-dimensioned geometry can only take this path.

```powershell
$py  = 'python'
$cli = 'scripts/maxwell_ece.py'
$mot = 'models/e11_PMSM_IPM.aedt'

& $py $cli inspect  $mot --write config/inspection.json      # Offline: read project structure
& $py $cli draft    $mot --design PMSM_Healthy --setup Setup1 --write config/draft.json
& $py $cli validate config/draft.json --inspection config/inspection.json
& $py $cli prepare  config/draft.json                        # Isolated copy
& $py $cli run      config/draft.json                        # Launch AEDT and solve
```

**Five-step flow:** the first three steps are offline (AEDT is not started), `prepare` copies the project into
an isolated working directory, and only `run` actually solves.

**`inspect` identifies everything automatically:** design names, setups, winding groups, and motion setups are
parsed from the `.aedt` text — nothing is hard-coded. When several designs or setups exist, `--design` and
`--setup` must be given explicitly; the tool will not choose for you (a wrong pick costs hours of solving).

**Output:** `<output_dir>/<run-id>/ece_model.sml` (import into Twin Builder) + `ece_table.txt` + `.sph`

**Core API chain** (not exposed directly by pyaedt 1.4.0; reached through native interfaces):

```python
write_ece_netlist(...)                              # Generate .sph from the vendor template
m2d.edit_external_circuit(netlist_file_path=sph)    # Attach to Maxwell
m2d.oanalysis.ExportECEData(export_args)            # Native ECE export
```

`ExportECEData` returns `None` on success — the return value cannot be used to judge the outcome;
check whether the files actually landed on disk.

---

## Development Roadmap

> **Goal:** An open-source, configuration-driven framework for permanent magnet synchronous motor (PMSM)
> modeling, multi-tool co-simulation, fault injection, and reproducible simulation experiments.

### Vision

Researchers and engineers should be able to define a PMSM model, operating conditions, control settings,
and fault scenarios in configuration files, then execute a repeatable simulation workflow without manually
rebuilding connections and settings in multiple engineering applications.

The framework integrates:

- **Ansys Motor-CAD:** rapid machine modeling and equivalent circuit export.
- **Ansys Maxwell:** finite-element modeling and ECE model extraction.
- **Ansys Twin Builder (Simplorer):** inverter, electrical power system, and machine circuit simulation.
- **MATLAB/Simulink:** motor control algorithms, including FOC and SVPWM, and closed-loop control.

### Current Status

| Component | Status | Scope |
|---|---|---|
| Motor-CAD ECE export | Implemented; further validation ongoing | Automated ECE data/model export and parameter extraction |
| Maxwell ECE extraction | Implemented; further validation ongoing | Scripted Maxwell ECE preparation and extraction workflow |
| Twin Builder–Simulink model binding | Implemented; further validation ongoing | Automated binding and generation of associated Simulink models |
| Twin Builder (Simplorer) + Simulink co-simulation automation | In development | Automate coupling of the power system and the control system |
| Configuration-driven PMSM fault simulation suite | In development | Fault setup, batch scenarios, simulation runs, and result export |

"Implemented" means working code and documentation are present in the repository,
**not** that every environment, model, or operating condition has been validated.

### Planned Architecture

```text
                   Configuration files
          (machine, operating conditions, faults,
               controller and solver settings)
                            |
                            v
                 Workflow orchestration
                            |
          +-----------------+-----------------+
          |                 |                 |
          v                 v                 v
      Motor-CAD          Maxwell        Fault scenarios
      ECE export       ECE extraction   and batch runner
          |                 |                 |
          +-----------------+-----------------+
                            |
                            v
               Twin Builder / Simplorer
                (PMSM + inverter + power)
                            <---->
                    MATLAB / Simulink
                     (FOC–SVPWM control)
                            |
                            v
               Simulation and data export
              (currents, voltages, speed,
                   torque, fault labels)
```

The diagram represents the **target architecture**; the complete end-to-end workflow is not yet released.

### Development Milestones

#### M1 — Existing Automation Tools

**Status:** Implemented; improvements ongoing.

- [x] Motor-CAD ECE export CLI and documentation.
- [x] Maxwell ECE extraction workflow and CLI.
- [x] Twin Builder–Simulink model binding automation.
- [x] Initial unit tests and example configurations.
- [ ] Expand compatibility testing and improve error reporting.
- [ ] Establish repeatable CI checks for tests that do not require commercial software.

#### M2 — Twin Builder (Simplorer) + Simulink Co-simulation

**Status:** In development. Design complete; no implementation code yet.

- [ ] Define configuration schema for the coupled power and control models.
- [ ] Automate Twin Builder circuit/project setup and Simulink controller binding.
- [ ] Support FOC–SVPWM closed-loop simulation configurations.
- [ ] Automate solver settings, signal exchange configuration, and run execution where supported by application APIs.
- [ ] Validate representative steady-state and dynamic speed/load scenarios.
- [ ] Export synchronized simulation outputs and run metadata.

**Exit criteria:** A documented sample can run a coupled PMSM power-system/control-system simulation from a
configuration file with clearly reported results and failures.

#### M3 — Configuration-driven PMSM Fault Simulation Suite

**Status:** In development. Research stage.

- [ ] Define a versioned schema for motor, fault, severity, operating conditions, and output settings.
- [ ] Implement fault-specific adapters where models and supported APIs permit.
- [ ] Target representative fault categories: inter-turn short circuit, winding open circuit, demagnetization,
      eccentricity, and inverter switch open circuit.
- [ ] Provide parameter sweeps over speed, load, fault severity, and selected noise conditions.
- [ ] Automate scenario execution, logging, and structured data export.
- [ ] Preserve fault labels, configuration snapshots, software versions, and run identifiers for reproducibility.

**Exit criteria:** Users can specify at least one validated fault type and multiple operating points via
configuration, execute the supported runs, and obtain labeled data and reproducible run records.

> **Safety and scope:** Fault implementation and physical fidelity depend on the underlying motor model and
> simulator. High-risk or unsupported fault conditions are not assumed to be validated by automation alone.

#### M4 — Reliability, Documentation, and Community Adoption

**Status:** Planned.

- [ ] Add end-to-end example projects with explicitly stated prerequisites.
- [ ] Expand offline unit and regression tests, plus optional integration tests for licensed software environments.
- [ ] Document application-version compatibility and known limitations.
- [ ] Add contributor guidance, issue templates, and a release process.
- [ ] Publish tagged releases with change logs and validation notes.
- [ ] Gather genuine community feedback through issues, discussions, and contributions.

### Why the work is staged this way

Closed-loop co-simulation needs a stable machine-side model first. The ECE models produced by the three released
tools are exactly that input. Building the machine side solidly before adding the power stage and the controller
avoids two simultaneous uncertainties — when something misbehaves, you know which layer to look at.

### Contribution Opportunities

Contributions are welcome in Python automation, test coverage, configuration validation, error diagnostics,
documentation, and reproducible simulation examples. For integration changes, please report the Ansys and
MATLAB/Simulink versions used and distinguish results verified in the commercial tools from offline-only tests.

### Dependencies and Limitations

- The repository's automation code is open source, but **Ansys and MATLAB/Simulink are proprietary** and require
  appropriate licenses for integration and simulation.
- Exact automation support and solver behavior can vary by software version, model, and environment.
- Milestones describe intended work, not guaranteed features or delivery dates.
- AI-assisted contributions are reviewed and validated before being treated as supported functionality.

### Status Updates

Progress is tracked through repository commits, issues, pull requests, and releases.
This roadmap will be updated as features are implemented and validated.

---

## Case study: BMW i3 (e11) IPM motor

Every model and configuration in this repository is centered on this machine:

| Parameter | Value |
|---|---|
| Poles / pole pairs | 8 / 4 |
| Stator outer diameter | 198 mm |
| Slots | 48 |
| Conductors per slot / turns per conductor | 108 / 6 |
| Parallel paths | 2 |
| Phase resistance Rs | 13.377 mΩ |
| Permanent magnet flux λpm | 0.075883 Wb |
| Ld (rated / saturated) | 198.2 / 226.3 µH |
| Lq (rated / saturated) | 378.6 / 297.4 µH |
| Saliency ratio | 1.91 |
| DC bus voltage | 400 V |
| Peak current | 433 A |

Control parameters derived from the ECE data (recomputable with `dist/ece-export/scripts/calc_control_params.py`):

| Parameter | Value |
|---|---|
| MTPA operating point (measured optimum) | Id = −307.9 A, Iq = 298.3 A → 246.4 N·m |
| Current-loop Kp_d / Ki_d | 1.246 / 84.05 |
| Current-loop Kp_q / Ki_q | 2.379 / 84.05 |
| Achievable torque by speed | 4000 rpm: 246 N·m · 6000 rpm: 202 N·m · 10000 rpm: 117 N·m |

> Inductances are **back-derived from flux linkage** (`Lq = λq/iq`, `Ld = (λd − λpm)/id`), not read from the
> `Ld`/`Lq` fields in the MAT file — the latter are division-by-zero artifacts near zero current, with units
> that do not match the declared `varUnits`.

Model samples:

```
models/
├── motorcad/e11_User.mot           Motor-CAD model (Full Machine state)
└── aedt/E11_FULL/e11_PMSM_IPM.aedt Maxwell 2D, with PMSM_Healthy + PMSM_UD designs

dist/maxwell-ece/models/e11_PMSM_IPM.aedt   The same project shipped with tool 3
```

---

## Repository layout

```
ansys-simulink-pmsm-cosimulation/
├── dist/                       Self-contained, independently usable tool packages
│   ├── simulink-binding/       Tool 1: Twin Builder ⇄ Simulink binding
│   ├── ece-export/             Tool 2: Motor-CAD ECE export
│   └── maxwell-ece/            Tool 3: Maxwell native ECE extraction
├── src/
│   ├── motorcad_controller/    Motor-CAD control
│   ├── simulink_controller/    Simulink binding
│   └── data_exchange/          .aedt parsing and data models
├── scripts/                    CLI entry points
├── config/                     Configuration
├── models/                     Sample motor models
└── tests/                      Unit tests
```

---

## Requirements

| Component | Version | Notes |
|---|---|---|
| Python | 3.12 | conda environment recommended |
| ansys-motorcad-core | 0.8.8 | Motor-CAD control |
| pyaedt | 1.4.0 | AEDT control (import path `ansys.aedt.core`) |
| matlabengine | 24.2 | Pairs with MATLAB R2024b |
| AEDT | 2026 R1 | Including Maxwell 2D/3D and Twin Builder |
| Motor-CAD | 2026 R1 | |
| MATLAB | R2024b | |

The license server address is configured per machine (`ANSYSLMD_LICENSE_FILE`); it is not stored in the repository.

---

## Quick start

```powershell
# 1. Install dependencies
conda create -n pmsm python=3.12
conda activate pmsm
pip install ansys-motorcad-core==0.8.8 pyaedt==1.4.0 matlabengine==24.2

# 2. Run the unit tests (Ansys and MATLAB not required)
python -m pytest tests/ -q

# 3. Use each tool individually — see its own README
```

---

## A note on how these tools came to be

These tools were **not designed up front and then implemented** — they were shaped by real engineering work.
That is why the code and READMEs retain a large amount of measured detail:

- which API does not work, and which path around it does
- what goes wrong when a parameter is set incorrectly (the grid must contain 0 A, for instance)
- which approaches were tried and abandoned, and why

That record is worth more to the next person than the conclusions alone — the same mistakes need not be made twice.

---

## License

The code in this repository is released for research on motor simulation automation.
Motor parameters (BMW i3) derive from publicly available sources.
Ansys and MATLAB are commercial software and require their own licenses.
