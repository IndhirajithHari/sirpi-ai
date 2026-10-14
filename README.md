# Sirpi

Sirpi is a local CPU-powered FreeCAD agent adapted from
[Taiga-S1](https://github.com/shhivv/taiga-s1) by Shiv Shanmugam.
It uses the original released model weights and retains the MIT attribution.
This is a renamed source adaptation, not a newly trained model.

Provide an **ordered, dimensioned feature goal** and the model selects FreeCAD
commands to build it. The vocabulary includes sketches, pads, pockets, holes,
patterns, mirrors, fillets, chamfers and shells. A natural-language planner and
general drawing/image-to-CAD conversion are not included.

## Windows setup

For a complete walkthrough, see **[Step-by-step Sirpi + FreeCAD setup](docs/SETUP.md)**.
It covers a fresh installation, connecting the macro, the first model, saved
files, restarting and troubleshooting.

### Quick start after installation

First complete the installation steps below or follow the detailed setup guide.
The commands work from any location where the complete Sirpi project is stored.

1. Open PowerShell in your Sirpi project folder.
2. Launch FreeCAD and run the Sirpi demo (skip the first command if Sirpi's
   FreeCAD server is already running):

```powershell
.\scripts\start-sirpi.ps1
.\.venv\Scripts\python.exe -m sirpi demo --level 3 --seed 7
```

If FreeCAD is not found automatically, supply its installed executable path:
`.\scripts\start-sirpi.ps1 -FreeCAD "C:\path\to\FreeCAD.exe"`.
The demo saves its model and preview in `runs\sirpi`.

### First-time installation

Install [FreeCAD for Windows from the official website](https://www.freecad.org/downloads.php).
Use Python 3.11+ and FreeCAD (upstream evaluated with FreeCAD 1.1).
From this folder in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 120 torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m sirpi doctor
.\.venv\Scripts\python.exe -m sirpi smoke
```

`smoke` loads the included weights and checks CPU inference without FreeCAD.
`doctor` returns status 1 when dependencies or the FreeCAD executable are missing.
Finding an executable alone does not establish runtime compatibility.

Start FreeCAD with Sirpi, substituting your installation path:

```powershell
.\scripts\start-sirpi.ps1 -FreeCAD "C:\Program Files\FreeCAD 1.1\bin\FreeCAD.exe"
.\.venv\Scripts\python.exe -m sirpi demo --level 3 --seed 7
```

If the macro does not start automatically, execute `scripts/Sirpi.FCMacro` from
FreeCAD's Macro menu in the launched window. The launcher supplies `SIRPI_REPO`.
The server listens on localhost port 8765. To change it, use `-Port` on the
launcher and `--port` on the demo.

To build a supplied goal:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --goals showcase/goals.json --name flange --out runs/flange
```

Outputs are `Sirpi.FCStd`, `Sirpi.png` and `result.json` in the output folder.
Use a different `--out` folder for each result you want to keep. Success requires
both Done and a target match; failed rollouts return a nonzero status and save
their result for inspection.

## Development

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The core Python package remains `freecad_s1` for compatibility with upstream
checkpoints and scripts. The installed distribution and command are `sirpi`.
`from freecad_s1.model.net import from_pretrained` and
`from freecad_s1.rollout import Policy` provide the original Python API.

Windows headless integration tests require a FreeCAD-compatible interpreter
and explicit `FREECAD_PYTHON` / `FREECAD_LIB`. The GUI macro runs inside FreeCAD
and avoids that headless discovery path. Live geometry validation must be done
with FreeCAD installed, separately from neural-model unit tests.

The upstream Mesa accessibility research code is preserved, but its macOS
workflows are outside Sirpi's Windows launcher. Large videos, old training
checkpoints, visualization assets and Mesa weights were excluded. Some
historical research scripts reference those excluded assets.

See [architecture](docs/ARCHITECTURE.md), [source provenance](NOTICE.md), and
[the original README](docs/UPSTREAM_README.md). Historical upstream benchmark
numbers are not new Sirpi measurements.

Current local checks and their limits are recorded in [validation](docs/VALIDATION.md).
