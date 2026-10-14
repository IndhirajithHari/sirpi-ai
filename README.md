# Sirpi AI

**A local AI agent that builds editable 3D parts in FreeCAD using CPU inference.**

Sirpi takes an ordered set of modeling features and dimensions, then selects
FreeCAD commands to construct the part. Watch the model build in FreeCAD and
inspect the resulting feature tree, preview image and evaluation report.

### [Download Sirpi AI — ZIP](https://github.com/IndhirajithHari/sirpi-ai/archive/refs/heads/main.zip)

Download the source and included model weights, extract the ZIP, and follow the
setup guide below. Git is optional. Python and FreeCAD are installed separately.

[Getting started](#getting-started) ·
[Usage](#step-6--build-your-first-part) ·
[Troubleshooting](#troubleshooting) ·
[Detailed setup](docs/SETUP.md) ·
[Source code](https://github.com/IndhirajithHari/sirpi-ai)

## Overview

| Feature | Description |
| --- | --- |
| Local CPU inference | Runs the included AI model without a GPU, API key or paid service. |
| FreeCAD integration | Builds parts in the desktop application with an editable feature tree. |
| Structured goals | Uses ordered modeling features and dimensions to guide construction. |
| Saved results | Exports a FreeCAD document, preview image and evaluation report. |

Sirpi supports sketches, pads, pockets, holes, patterns, mirrors, fillets,
chamfers and shells. It currently accepts structured feature goals; arbitrary
text prompts and drawing/image-to-CAD conversion are not supported.

## Getting started

This guide covers **Windows and PowerShell**. The recorded setup was validated
with **Python 3.12 and FreeCAD 1.1.4**. Other operating systems may require
additional setup; see [validation results](docs/VALIDATION.md).

Downloading the public repository does not require a GitHub account. All paths
below are relative to your downloaded project folder, regardless of your Windows
username or where you save the project.

### Step 1 — Install the prerequisites

| Requirement | Installation |
| --- | --- |
| 64-bit Python 3.11+ | Install from [Python for Windows](https://www.python.org/downloads/windows/). Python 3.12 was used for validation. Enable the option to add Python to PATH. |
| FreeCAD | Install from [the official FreeCAD website](https://www.freecad.org/downloads.php). FreeCAD 1.1.4 was used for validation. |
| Git (optional) | Install [Git for Windows](https://git-scm.com/download/win) if using the clone option below. ZIP download does not require Git. |

Open **PowerShell** after installation. All commands below are PowerShell
commands. Run each line in order and wait for it to finish. If a command fails,
resolve the error before continuing.

### Step 2 — Download and open the project

Choose **one** of these options.

**Option A — Download ZIP (recommended for first-time users)**

1. Click **[Download ZIP](https://github.com/IndhirajithHari/sirpi-ai/archive/refs/heads/main.zip)**.
2. Right-click the downloaded ZIP and choose **Extract All**.
3. Open the extracted `sirpi-ai-main` folder containing `README.md` and `pyproject.toml`.
4. Click File Explorer's address bar, type `powershell`, and press **Enter**.
   PowerShell will open in that project folder.

**Option B — Clone with Git**

Open PowerShell and copy these commands. The repository URL is the same for
all users; copy it without modification.

```powershell
cd $HOME
git clone https://github.com/IndhirajithHari/sirpi-ai.git
cd .\sirpi-ai
```

For either option, keep this PowerShell window open for the remaining steps.
Check that you are in the correct folder:

```powershell
Test-Path .\pyproject.toml
```

The result should be `True`.

### Step 3 — Install Sirpi

Copy and run these commands from the project folder:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --timeout 120 torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install --timeout 120 -e ".[dev]"
```

The first command should show Python 3.11 or later. Installation needs internet
access and downloads CPU-only PyTorch and the remaining dependencies. Virtual
environment activation is unnecessary. Complete this step once per computer.

### Step 4 — Verify the installation

```powershell
.\.venv\Scripts\python.exe -m sirpi doctor
.\.venv\Scripts\python.exe -m sirpi smoke
```

Expected results:

- `doctor`: all dependencies are `true`, `freecad_gui` contains an executable
  path, and `local_weights` is `true`.
- `smoke`: reports `"device": "cpu"`, `"parameters": 1228163`, and action
  probabilities. This verifies inference without building geometry.

If FreeCAD is not detected, set its actual installation path and retry. The
following is an example; adjust it if FreeCAD is installed elsewhere:

```powershell
$env:SIRPI_FREECAD = "C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
.\.venv\Scripts\python.exe -m sirpi doctor
```

### Step 5 — Launch FreeCAD

```powershell
.\scripts\start-sirpi.ps1
```

Wait for the FreeCAD window to finish opening and leave it open. The launcher
runs the Sirpi macro, which starts a local server on port **8765**. If a
Sirpi-enabled FreeCAD window is already running, reuse it and skip this command.

If the macro does not start automatically, open **Macro → Macros…** in the
launched FreeCAD window, select the project's `scripts` folder, select
**Sirpi.FCMacro**, and click **Execute**. FreeCAD's Report view should show:

```text
Sirpi GUI server listening on 127.0.0.1:8765
```

### Step 6 — Build your first part

Return to the same PowerShell window and run:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --level 3 --seed 7 --out runs\first-part
```

Watch FreeCAD create a cylinder, a hole pattern, a cylindrical boss and a fillet.
Wait for the command to finish before manually editing the document.

The [recorded validation run](docs/VALIDATION.md) completed this example in
26 commands with the following result:

```json
{
  "success": true,
  "done": true,
  "steps": 26,
  "iou": 1.0
}
```

`iou` measures geometric overlap with the target; `1.0` is an exact match.
These are recorded results, not a guarantee for every environment or goal.

### Step 7 — Open and inspect the results

Open the result folder:

```powershell
Invoke-Item .\runs\first-part
```

| File | What to inspect |
| --- | --- |
| `Sirpi.FCStd` | Open in FreeCAD to inspect the editable model and feature tree. |
| `Sirpi.png` | Preview of the generated part. |
| `result.json` | Completion status, command count, geometric overlap and saved paths. |

Use a new `--out` folder for each result you want to keep. Reusing a folder can
replace its previous outputs. Failed rollouts return a nonzero status and save
results for inspection.

### Step 8 — Run another example

With the same Sirpi-enabled FreeCAD window open:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --goals showcase\goals.json --name flange --out runs\flange
```

The included [goal file](showcase/goals.json) contains structured modeling goals.
For all available demo options:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --help
```

### Step 9 — Stop and restart Sirpi

1. Wait for the running demo to finish.
2. Save any manual changes to the model and close FreeCAD normally.
3. When you want to run Sirpi again, open your project folder in File Explorer.
4. Type `powershell` in its address bar and press **Enter**.
5. Run the launcher below, wait for FreeCAD to open, then run the demo:

```powershell
.\scripts\start-sirpi.ps1
.\.venv\Scripts\python.exe -m sirpi demo --level 3 --seed 7 --out runs\next-part
```

Reuse an existing Sirpi-enabled FreeCAD window by skipping the launcher.
Choose a new output folder to preserve earlier results. You do not need to
repeat installation each time.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| `python` is not recognized | Install Python with its PATH option enabled, then reopen PowerShell in the project folder. |
| `pyproject.toml` is not found | Open the extracted or cloned folder that actually contains that file; a ZIP may contain an extra folder level. |
| `.venv\Scripts\python.exe` is missing | Run Step 3 from the project folder. |
| `No module named sirpi` | Rerun Step 3's final editable-install command. |
| FreeCAD is not detected | Set `SIRPI_FREECAD` to the actual executable path as shown in Step 4. |
| PowerShell blocks `.ps1` scripts | Use the direct executable-and-macro startup instructions in Step 6 of the [detailed setup guide](docs/SETUP.md). |
| Cannot reach Sirpi on port 8765 | Leave FreeCAD open, wait for startup and check that the macro is running. For slow startup, add `--wait 120` to the demo command. |
| `Set SIRPI_REPO` appears in FreeCAD | Save and close that session, then launch it with Step 5's script. |
| A dependency download times out | Retry the failed installation command; the commands above include an extended timeout. |
| `success: false` | Inspect `result.json` and FreeCAD's errors. Reproduce the level 3 / seed 7 example before trying more complex goals. |

## Validation and development

The Windows GUI workflow is documented and locally validated. A successful
sample establishes working integration, not general accuracy on arbitrary
parts. Other operating systems and FreeCAD versions may require additional
setup and compatibility checks.

For optional automated verification:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Live headless FreeCAD integration tests require additional configuration;
see [the detailed setup guide](docs/SETUP.md) and
[recorded validation results](docs/VALIDATION.md). Model unit tests alone do not
validate CAD geometry.

## Attribution and project documentation

Sirpi is adapted from [Taiga-S1](https://github.com/shhivv/taiga-s1) by
Shiv Shanmugam and uses its original released model weights. Sirpi adds its
CLI, diagnostics, CPU inference check, Windows launcher, GUI rollout client,
tests and setup documentation. It is a source adaptation, not a newly trained
model. The core package remains `freecad_s1` for upstream compatibility.

Original MIT attribution is preserved in [LICENSE](LICENSE) and
[NOTICE.md](NOTICE.md). Historical upstream benchmarks are not new Sirpi
measurements. Some retained research scripts reference excluded assets or
macOS workflows outside this Windows demo.

- [Architecture](docs/ARCHITECTURE.md)
- [Detailed setup](docs/SETUP.md)
- [Validation results](docs/VALIDATION.md)
- [Source provenance](NOTICE.md)
- [Original upstream README](docs/UPSTREAM_README.md)
