# Sirpi validation — 2026-10-13

Environment: Windows, Python 3.12.14, PyTorch 2.14.1+cpu, NumPy 2.5.4,
safetensors 0.8.0, huggingface_hub 2.2.0, pytest 9.1.1.
The editable `sirpi==0.1.0` package is installed in the workspace `.venv`.

## Passed

- `python -m pytest -q -ra`: **35 passed, 9 skipped**, 24.97 seconds.
  This includes upstream model/expert tests, portable UI logic and Sirpi's
  CLI, protocol and rollout-result tests. `OMP_NUM_THREADS=1` was used.
- `python -m sirpi smoke`: loaded the unchanged local weights on CPU,
  counted **1,228,163 parameters**, and produced finite normalized probabilities
  over the valid command set. Highest-scoring command for the synthetic initial
  state was `Std_New` (0.51223). This check does not build CAD geometry.
- `sirpi --version`: `Sirpi 0.1.0`.
- `python -m pip check`: no broken requirements.
- Python source compilation and PowerShell launcher syntax check passed.
- 98 unchanged imported files matched their Git blob hashes at the pinned
  upstream revision. The five modified imported files are identified in
  `UPSTREAM_MANIFEST.json`.

Model SHA-256:
`7ad63f77399eaddd3aebae0d0cf493340885d741a9fe51c1e4737f7273a1408c`

## Live FreeCAD setup completed

Later on 2026-10-13, FreeCAD **1.1.4** was detected at
`C:\Program Files\FreeCAD 1.1\bin\freecad.exe`. `sirpi doctor` now passes.

- Launched the installed GUI with `scripts/start-sirpi.ps1` and its Sirpi macro.
- Ran `sirpi demo --level 3 --seed 7 --delay 0.1 --out runs/setup-validation`.
  The CPU policy built a base cylinder, hole, polar pattern, cylindrical boss
  and top fillet in **26 commands**, ending with Done and **IoU 1.0**.
- Saved `runs/setup-validation/Sirpi.FCStd`, `Sirpi.png` and `result.json`.
  Visually inspected the exported preview.
- Reopened the saved document using FreeCAD's bundled Python: **one valid solid**,
  volume 68852.74901416748, final feature `PartDesign::Fillet`.
- Ran both actual FreeCAD integration tests: **2 passed in 39.62 seconds**.
  The test process used `FREECAD_PYTHON=C:\Program Files\FreeCAD 1.1\bin\python.exe`
  and `FREECAD_LIB=C:\Program Files\FreeCAD 1.1\bin`. These were process-local
  variables; machine-wide environment settings were not changed.

The first GUI-client attempt was blocked by the agent's sandbox networking;
the authorized localhost connection outside that sandbox succeeded without a
code change. Ordinary local PowerShell use does not involve that agent sandbox.

The initial suite's two skipped FreeCAD tests have now passed in the separate
integration run. Six POSIX watchdog tests and the macOS-only module remain
outside this Windows validation. A single successful neural demo establishes
working integration, not general accuracy on arbitrary parts.
