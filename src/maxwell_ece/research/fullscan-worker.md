# ECE full-scan worker ledger

Date: 2026-10-17

Scope: offline implementation under `versions/v0.3/maxwell_ece` only. No AEDT,
MATLAB, Simulink, GUI, or native solver was started by this worker. Source
projects and existing smoke outputs were left unchanged.

Implemented:

- `ece/core.py` now calculates a labelled `estimated_base` ECE point count,
  parses real native ECE `logfile` facts, and never treats that estimate as a
  native counter denominator.
- Prepare and live stages write machine-readable `progress.json` and
  `timing-result.json`, including UTC start/completion timestamps, duration,
  stage, status, and errors.
- Live solve remains synchronous through the verified `analyze_setup` API. A
  daemon tail monitor reads known `logfile` paths below the prepared job and
  reports only explicit native counters when they exist.
- `ece/cli.py` renders elapsed/stage/ETA progress. Unknown native percentage
  remains `?%` with `ETA unavailable`. Batch runs can write a separate
  aggregate JSON using `--progress-json`.
- Added formal and optional diagnostic configurations:
  `config/full360-PMSM_Healthy.json` and
  `config/initial-full360-3mag-PMSM_Healthy.json`.
- Added tests for the existing native logfile format, explicit-counter parsing,
  estimate labelling, and prepare timing evidence.

Offline commands run:

```powershell
C:\Env\miniconda3\envs\pmsm\python.exe -m unittest discover -s versions/v0.3/maxwell_ece/tests -v
C:\Env\miniconda3\envs\pmsm\python.exe versions/v0.3/maxwell_ece/scripts/maxwell_ece.py validate versions/v0.3/maxwell_ece/config/full360-PMSM_Healthy.json
C:\Env\miniconda3\envs\pmsm\python.exe versions/v0.3/maxwell_ece/scripts/maxwell_ece.py validate versions/v0.3/maxwell_ece/config/initial-full360-3mag-PMSM_Healthy.json
```

Root-owned probe/full run commands:

```powershell
$py = 'C:\Env\miniconda3\envs\pmsm\python.exe'
$cli = '.\versions\v0.3\maxwell_ece\scripts\maxwell_ece.py'
& $py $cli inspect .\models\aedt\E11_FULL\e11_PMSM_IPM.aedt --write .\versions\v0.3\maxwell_ece\config\inspection-full360.json
& $py $cli validate .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json --inspection .\versions\v0.3\maxwell_ece\config\inspection-full360.json
& $py $cli prepare .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json
& $py $cli run .\versions\v0.3\maxwell_ece\config\full360-PMSM_Healthy.json
```

The final command starts AEDT and is intentionally reserved for root. Shared
workflow/evidence state was not modified by this worker.
