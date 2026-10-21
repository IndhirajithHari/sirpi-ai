# Sirpi Chat

Sirpi Chat is a docked panel inside FreeCAD. It translates a small set of text
request formats into structured goals and sends them through the existing
CPU model and FreeCAD command workflow. No cloud service or API key is used.

## Start and build

1. Complete the installation steps in the [README](../README.md).
2. Open PowerShell in the project folder and run `.\scripts\start-sirpi.ps1`.
3. In the **Sirpi Chat** panel, choose an example or type a request.
4. Press **Enter** or click **Review request** and check the dimensions shown
   in the conversation. **Shift+Enter** inserts a new line without submitting.
5. Click **Build part**. Wait for completion before editing the model.
6. Click **Open result folder** to find the model, preview and build report.

Closing the dock hides it. Reopen it through **View → Panels → Sirpi Chat** or
run `scripts/Sirpi.FCMacro` again. Running the macro again reuses the same panel.
An ordinary FreeCAD shortcut does not automatically load Sirpi.

## Supported requests

Use these example formats; optional `Create`, `Make`, `Build`, `Please`, and
`a` prefixes are accepted. Dimensions are millimetres, including when `mm` is
omitted. Decimal dimensions and separators `x`, `×`, `*` and `by` are accepted.
Square and rectangle requests can use `at`, `size`, `of size` or `measuring`
before their dimensions.

```text
Create a plate 100 x 60 x 8 mm
Make a square at 2*2*0.5mm
Make a rectangle 40 by 20 by 3 mm
Create a plate 100 x 60 x 8 mm with 4 holes diameter 6 mm inset 10 mm
Create a plate 100 x 60 x 8 mm with a center hole diameter 12 mm
Create a cylinder diameter 40 mm height 20 mm
Create a cylinder diameter 40 mm height 20 mm with a center hole diameter 10 mm
Create a ring outer diameter 60 mm inner diameter 30 mm height 10 mm
```

- Plate dimensions are width × depth × thickness, aligned with X × Y × Z.
- `box` and `block` are aliases for a plate-shaped rectangular solid.
- `rectangle` also creates a rectangular solid. `square` requires equal width
  and depth; the thickness can be different.
- Diameters are converted to radii for the model's goal representation.
- Holes go all the way through the part.
- Four-hole inset is measured from each hole's center to the two adjacent
  plate edges. The review shows the exact X/Y center coordinates.
- Each dimension must be between 0.1 and 1000 mm. Holes must fit inside the
  base without touching its edges or each other. A ring's inner diameter must
  be smaller than its outer diameter.

To enter dimensions in a second message:

```text
You: Create a cylinder
Sirpi: What diameter and height in mm?
You: diameter 40 mm height 20 mm
```

Two dimensions describe an outline, so Sirpi asks for thickness instead of
guessing it:

```text
You: make a square at 2*2mm
Sirpi: I read a 2 × 2 mm outline. To make a solid part, what thickness should it have?
You: 0.5 mm
```

Press **Enter** after each message, then click **Build part** once the complete
dimensions appear in the review. This creates a 2 × 2 × 0.5 mm solid plate.
The chat workflow currently builds solids, not standalone 2D sketches.

Changing the input invalidates the previous plan. Review the new request before
building.

## Follow-up: add a center hole

After building a plate or cylinder successfully in this chat:

```text
You: now add a hole in centre at 1mm
Sirpi: Does 1 mm mean the hole diameter or radius?
You: diameter
```

Review the resulting dimensions and click **Build part**. Alternatively, send
`add a center hole diameter 1 mm` or `add a center hole radius 0.5 mm`.
The hole goes through the full thickness. If it would touch the outside edge
or overlap another hole, Sirpi asks for a smaller size. A part that already has
a center hole cannot receive another one through this follow-up.

The basis is the **last successful chat build**, not a merely reviewed,
failed or cancelled request, and not whichever FreeCAD tab is selected.
The revised goal is rebuilt in a new document; the original stays open.
Existing chat-created holes are retained. Manual edits in FreeCAD are not
included in the revised copy. Memory is local to this running chat session;
build the base again after restarting FreeCAD.

## Results and cancellation

Each build has a unique folder under `runs/chat`:

| File | Purpose |
| --- | --- |
| `goal.json` | Structured goal from the reviewed request |
| `Sirpi.FCStd` | Editable FreeCAD model |
| `Sirpi.png` | Model preview |
| `result.json` | Completion, target overlap and saved paths |
| `build.log` | Model actions and error output |

Successful builds require both the model's Done action and at least 99% target
overlap, matching the existing rollout validation. The panel reports failures
without claiming the part succeeded. Very small, large or unusual proportions
can fail even when the request passes input checks.

**Stop** terminates the inference process. Any partial model remains open but
may not have been saved or validated. The same applies to the three-minute
timeout. Previous documents and their manual edits stay open when a new chat
build starts. Save manual edits using FreeCAD before closing the application.

Use one build at a time; do not start command-line demos while a chat build is
running. The panel detects an already connected client before starting its own.

## Limits

This is a template-based text interface, not a general language model. It does
not generate or execute Python from user text. Unsupported words, extra
features and non-mm units are rejected. It cannot currently design gears,
brackets, assemblies, threads or parts from drawings. Conversational changes
are limited to adding a center hole to the last successful plate/cylinder goal.
Other changes use FreeCAD's normal editing tools or a new complete request.

## Developer checks

Run parser and CLI checks from the project environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_chat.py tests\test_sirpi.py -q
```

For live GUI validation, start a dedicated FreeCAD session with the project
environment and execute `scripts/test-chat.FCMacro`. It uses port 8766 by
default (or `SIRPI_PORT`), drives the actual panel and CPU inference process,
checks the five original examples, the square prompt and its center-hole follow-up
against analytic volumes and exact bounding boxes, and checks Enter submission, clarification, cancellation
and document preservation. It leaves
the test documents open and writes `runs/chat-gui-test.json`.
