# Set up Sirpi with FreeCAD on Windows

Sirpi runs its AI model in a separate Python process and controls FreeCAD through
a macro. It does not appear as a workbench or an Addon Manager extension. Keep
the FreeCAD window open while running Sirpi commands from PowerShell.

These instructions apply to a fresh installation for any user. Start at Step 1
for first-time setup, or Step 4 to check an existing installation.
`C:\Projects\Sirpi` is an example project location; replace it with the folder
where you extracted the competition project. All relative paths are measured
from that folder. FreeCAD installation paths are also examples and may differ.

## Step 1 — Install FreeCAD

1. Visit the [official FreeCAD download page](https://www.freecad.org/downloads.php).
2. Choose the stable **Windows x86_64 installer** and complete installation.
3. Note the installation folder. An example executable path is:
   `C:\Program Files\FreeCAD 1.1\bin\freecad.exe`.

Sirpi was validated with FreeCAD 1.1.4. Different versions may need additional
compatibility checks. You do not need to install PyTorch inside FreeCAD.

## Step 2 — Prepare the Sirpi project and Python

If you have already prepared the project and Python, continue to Step 3.

1. Place the complete Sirpi project in a folder, for example
   `C:\Projects\Sirpi`. When transferring it to another computer,
   copy the source and `release\hf` model files, but recreate `.venv` there.
   Cloning the original Taiga repository alone does not include Sirpi's additions.
2. Install a 64-bit Python version supported by the project's dependencies.
   This setup was tested with Python 3.12; the project requires Python 3.11+.
3. Open **PowerShell** from the Windows Start menu.
4. Change to the project folder. Substitute your own path if necessary:

```powershell
cd "C:\Projects\Sirpi"
python --version
```

The folder must contain `pyproject.toml`, `sirpi`, `freecad_s1`, `scripts` and
`release\hf`. If `python` is unavailable, finish installing Python and reopen
PowerShell before continuing.

## Step 3 — Install Sirpi's Python dependencies

Skip this step if the existing `.venv` is working. Run these commands one at a
time in PowerShell, waiting for each to finish:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --timeout 120 torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install --timeout 120 -e ".[dev]"
```

The first command creates a project-specific Python environment. The second
installs CPU-only PyTorch. The third installs Sirpi and its remaining dependencies.
Internet access is needed for these downloads. No GPU or API key is required.
The commands use the environment's Python directly, so activation is unnecessary.

## Step 4 — Check the installation

Open PowerShell and run:

```powershell
cd "C:\Projects\Sirpi"
.\.venv\Scripts\python.exe -m sirpi doctor
.\.venv\Scripts\python.exe -m sirpi smoke
```

For `doctor`, check that:

- `torch`, `numpy`, `safetensors` and `huggingface_hub` are all `true`.
- `freecad_gui` contains the installed FreeCAD executable path.
- `local_weights` is `true` for this supplied project.

The `smoke` check should report `device: "cpu"`, `parameters: 1228163` and a
list of command probabilities. It verifies the AI model without building a part.
If the weights are missing, the default loader may try downloading the original
model from Hugging Face. Keep both `release\hf\config.json` and
`release\hf\model.safetensors` to use the supplied model locally.

For an installation that is not automatically detected, set the executable
location in the current PowerShell session and repeat `doctor`:

```powershell
$env:SIRPI_FREECAD = "C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
.\.venv\Scripts\python.exe -m sirpi doctor
```

## Step 5 — Launch FreeCAD with the Sirpi connection

Save any work already open in FreeCAD. Use a dedicated FreeCAD session for Sirpi
so its modeling commands do not interfere with manual editing.

From the Sirpi project folder, run:

```powershell
.\scripts\start-sirpi.ps1
```

If automatic discovery fails, specify the actual executable:

```powershell
.\scripts\start-sirpi.ps1 -FreeCAD "C:\Program Files\FreeCAD 1.1\bin\freecad.exe"
```

Wait for FreeCAD to finish opening. The launcher supplies the project location
through `SIRPI_REPO` and runs `scripts\Sirpi.FCMacro`. The macro starts a local
server on port **8765**. A successful startup prints:

```text
Sirpi GUI server listening on 127.0.0.1:8765
```

The message may appear in FreeCAD's Report view rather than in PowerShell.
The launcher's own "launched" message only confirms that it started the app;
the first successful demo confirms the connection.

If a Sirpi-enabled FreeCAD window is already running, reuse it and skip this
launch command. Opening an ordinary FreeCAD shortcut does not automatically
start the Sirpi macro.

## Step 6 — Start the macro manually if needed

If FreeCAD opened through the launcher but Sirpi cannot connect:

1. In that FreeCAD window, open **Macro → Macros…**.
2. Set the macro directory/user macros location to
   the `scripts` folder inside your Sirpi project, for example
   `C:\Projects\Sirpi\scripts`.
3. Select **Sirpi.FCMacro** and choose **Execute**.
4. Leave FreeCAD open and retry Step 7.

If the macro says `Set SIRPI_REPO`, FreeCAD was started without the required
environment. Save your documents and close that FreeCAD window, then start it
using Step 5. Running the macro again in a window with the same missing
environment will not fix it.

If PowerShell prevents running `.ps1` files, you can launch the same executable
and macro directly from PowerShell without changing execution-policy settings:

```powershell
$env:SIRPI_REPO = (Get-Location).Path
$env:SIRPI_PORT = "8765"
& "C:\Program Files\FreeCAD 1.1\bin\freecad.exe" "$env:SIRPI_REPO\scripts\Sirpi.FCMacro"
```

Run this from the Sirpi project folder and substitute the FreeCAD path if needed.
If this command holds the terminal open, use a second PowerShell window in the
same project folder for Step 7.

## Step 7 — Build your first part

In PowerShell, with the Sirpi-enabled FreeCAD window open:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --level 3 --seed 7 --out runs\first-part
```

The model runs on CPU. Watch the feature tree and viewport as it creates the
part. Avoid editing the document while the demo is running. This example builds
a cylinder, a hole pattern, a cylindrical boss and a fillet. In the validation
run it completed in 26 commands with an exact target match.

At the end, inspect the printed result:

```json
{
  "success": true,
  "done": true,
  "steps": 26,
  "iou": 1.0
}
```

This excerpt shows the observed successful run, not a guarantee for every goal
or FreeCAD version. `iou` measures geometric overlap with the target; 1.0 is an
exact match. `success` also requires the model to finish with Done.

## Step 8 — Find and reopen the result

Open the `runs\first-part` folder inside your Sirpi project in File Explorer.

| File | Purpose |
| --- | --- |
| `Sirpi.FCStd` | Editable FreeCAD document and feature tree |
| `Sirpi.png` | Rendered preview |
| `result.json` | Success status, command count, geometric match and saved paths |

To reopen the model, use **File → Open** in FreeCAD and select `Sirpi.FCStd`.
Use a new `--out` folder for each run you want to keep; reusing a folder can
replace its result files.

## Step 9 — Build a supplied named goal

With the same FreeCAD server still running:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --goals showcase\goals.json --name flange --out runs\flange
```

The goal file supplies ordered modeling features and dimensions. Sirpi does not
yet accept arbitrary natural-language descriptions or images as modeling goals.
For all supported demo options, run:

```powershell
.\.venv\Scripts\python.exe -m sirpi demo --help
```

## Step 10 — Stop and restart later

After the demo finishes, save any manual edits and close FreeCAD normally. This
also stops its Sirpi server. Next time, repeat Steps 5 and 7; dependency
installation is a one-time step. If the server is still open, just repeat Step 7.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `.venv\Scripts\python.exe` is not found | Check the current folder. On a fresh computer, complete Steps 2–3. |
| `No module named sirpi` or a dependency is missing | From the project folder, rerun the final install command in Step 3 using `.venv` Python. |
| FreeCAD was not found | Supply the real executable path as shown in Steps 4–5. |
| `Cannot reach Sirpi on port 8765` | Keep FreeCAD open, allow startup to finish and follow Step 6. Check that client and server use the same port. |
| FreeCAD takes longer than the connection wait | Retry after startup or add `--wait 120` to the demo command. |
| `Set SIRPI_REPO` | Save and close that FreeCAD session, then relaunch through Step 5. |
| Port/address already in use | Reuse the existing Sirpi session, or choose a different port using the commands below. |
| A download times out | Repeat the failed pip command with `--timeout 120`; completed installations remain available. |
| `success: false` | Inspect `result.json` and the console's FreeCAD errors. Reproduce with the tested level/seed before trying a more complex goal. |

To use a different port, both commands must agree:

```powershell
.\scripts\start-sirpi.ps1 -Port 8766
.\.venv\Scripts\python.exe -m sirpi demo --port 8766 --out runs\port8766
```

Do not change the port only on the client. The server runs locally;
no router configuration or cloud service is required.

## Optional — Run the verification tests

Run portable model and CLI tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

To include the actual headless FreeCAD integration tests on Windows,
point the test process at FreeCAD's own Python and library directory:

```powershell
$env:FREECAD_PYTHON = "C:\Program Files\FreeCAD 1.1\bin\python.exe"
$env:FREECAD_LIB = "C:\Program Files\FreeCAD 1.1\bin"
.\.venv\Scripts\python.exe -m pytest tests\test_runtime.py -q
```

These variables apply to the current PowerShell session. They are unnecessary
for the normal GUI demo. See [validation results](VALIDATION.md) for the actual
recorded test results and the validation environment.
