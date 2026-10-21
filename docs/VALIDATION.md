# Sirpi validation

## Square-prompt regression fix — 2026-10-15

The prompt `make a square at 2*2mm` was previously rejected: the parser only
accepted plate/box/block names and `x`/`×` separators, and required three
dimensions. The panel also required clicking Review rather than pressing Enter.

- Added square and rectangle requests, `*`/`by` separators, common size wording,
  and a thickness question for two-dimensional outlines. A square must have
  equal width and depth. Unsupported units and extra features remain rejected.
- Enter submits for review; Shift+Enter inserts a newline. Clarification replies
  keep input focus and explain why Build is unavailable.
- Full suite: **81 passed, 7 platform-specific skips in 45.13 seconds**,
  including both actual headless FreeCAD integration tests.
- Live GUI regression: submitted the exact user prompt with an Enter key event,
  verified the thickness question, submitted `0.5 mm` with Enter, and clicked
  Build. FreeCAD produced one valid solid in **10 commands**, **IoU 1.0**,
  exact bounding box **2 × 2 × 0.5 mm**, and volume **2 mm³**.
- All five original chat examples and the cancellation/document-preservation
  checks also passed. The current `runs/chat-gui-test.json` contains all six
  successful builds. The square's local artifacts are in
  `runs/chat/20261015-001344-44c027f6`.

The 0.5 mm thickness is the regression test's explicit reply, not an inferred
default. The user must provide a thickness to turn an outline into a solid.

## Chat panel validation — 2026-10-15

Tested on Windows with the installed FreeCAD 1.1.4 and project Python 3.12
environment. The released model weights remain unchanged.

- Full suite with `FREECAD_PYTHON` and `FREECAD_LIB` pointing to the installed
  FreeCAD runtime: **69 passed, 7 skipped in 53.84 seconds**. The skips are six
  POSIX-only watchdog checks and one macOS module. The two headless FreeCAD
  integration tests passed as part of this run.
- `scripts/test-chat.FCMacro` exercised the actual Qt dock, review/build
  buttons, external CPU process, socket server, geometry and saved artifacts.
- Verified the dock is visible and reused when reopened; missing dimensions
  can be supplied in the next message; typing invalidates an old review;
  unsupported requests cannot be built; cancellation restores the controls;
  previous documents and a manual label edit survive subsequent builds.
- Inspected the visible chat panel and generated models in FreeCAD.
- All five examples below ended with Done, **IoU 1.0**, one valid solid and
  volume matching an independent analytic calculation (relative tolerance
  1e-6). Exact bounding boxes, excluding display tessellation, matched the
  requested dimensions within 1e-5 mm.

| Example | Commands | Bounding box (mm) | Volume (mm³) |
| --- | ---: | --- | ---: |
| Plate 100 × 60 × 8 | 10 | 100 × 60 × 8 | 48000.0000 |
| Same plate, four Ø6 through-holes, 10 mm inset | 38 | 100 × 60 × 8 | 47095.2213 |
| Cylinder Ø40, height 20 | 9 | 40 × 40 × 20 | 25132.7412 |
| Cylinder Ø40, height 20, center hole Ø10 | 16 | 40 × 40 × 20 | 23561.9449 |
| Ring outer Ø60, inner Ø30, height 10 | 10 | 60 × 60 × 10 | 21205.7504 |

The local machine-readable report is `runs/chat-gui-test.json`; individual
models, previews, goals, logs and results are in unique `runs/chat` folders.
These generated files are ignored by Git. Run the macro in a dedicated
FreeCAD session to reproduce the checks; see [the chat guide](CHAT.md).

This validates the five example requests and tested control flows, not every
dimension combination or unrestricted natural-language modeling. Chat uses
explicit request templates and creates new parts; conversational editing of
existing parts is not implemented. Process startup failure and the full
three-minute timeout were not exercised by this live validation.

## Original validation — 2026-10-13

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
