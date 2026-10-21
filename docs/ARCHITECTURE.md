# Sirpi architecture walkthrough

This documents an inspection of available source, rather than a reconstruction
from a closed binary. Sirpi preserves Taiga-S1's released neural policy.

## One modeling step

1. `runtime/session.py` or `runtime/gui_session.py` snapshots the live document:
   feature tree, sketch geometry/constraints, selection, workbench, recent
   commands and shape descriptors.
2. `schema.py` represents the state and ordered `GoalFeature` list.
   `actions.py` enumerates currently valid commands.
3. `model/featurize.py` encodes typed state tokens and candidate-action features.
4. `model/net.py` encodes the state with a transformer. Each candidate action
   queries that context. The released config has width 128, four attention
   heads, three encoder layers and two decoder layers.
5. A modular done head chooses the first unfinished goal item. Matching
   ordinals connect goal features to document objects. The decoder sees the
   state and active intent, then produces one score per candidate.
6. `rollout.Policy` chooses a command. Dimensions come from the goal via
   `runtime/params.py`. The runtime executes the command and snapshots again.
7. The runtime compares the final solid to a target constructed from the goal.
   Sirpi reports success only when the model emits Done and the target matches.

## Process boundary

```text
Sirpi / PyTorch (CPU)                 FreeCAD / Qt main thread
  structured goal  ---------------->  local JSON socket server
  state + commands <----------------  worker + GUI session
  chosen command   ---------------->  executor + parameter resolver
  updated state    <----------------  document snapshot
```

The protocol is newline-delimited JSON with an `@@S1 ` response prefix.
`runtime/gui_server.py` polls requests with a Qt timer on the GUI thread and
binds to loopback. Operations include reset, step, score and save. The server
is intended for trusted local clients. Sirpi validates response framing,
applies connection/read timeouts and closes the client after each run.

## Chat panel

`sirpi/chat.py` parses a deliberately limited set of plate, cylinder, ring and
hole request formats. It consumes the full request, validates dimensions and
returns a `Goal` plus a review summary. A conversation retains a bare shape
while asking for missing dimensions. Unsupported features are rejected.
Successful builds are copied into conversation memory. A validated center-hole
follow-up copies that goal, checks hole fit and overlap, and produces a new
reviewable goal. Ambiguous dimensions trigger a diameter/radius question.
Failed, cancelled and merely reviewed requests never replace the last successful
goal. The revised goal is rebuilt, so manual FreeCAD edits are not imported.

`sirpi/chat_panel.py` provides the FreeCAD Qt dock, opened by `Sirpi.FCMacro`.
After the user reviews a goal and clicks Build, the panel writes `goal.json`
into a unique output folder and starts the existing `sirpi demo` command with
`QProcess`. Qt remains available while inference runs in the project Python
environment. Progress, completion, cancellation and failure are reported in
the panel; user text is never evaluated as Python or a shell command.

Before a chat build, the GUI session releases ownership of its previous
document so the existing reset operation cannot close it or discard manual
edits. Existing unrelated documents also remain open. This preservation applies
to builds started from the panel; the original CLI reset semantics are unchanged.

## Training and weights

`datagen.py`, `expert.py` and the runtime produce synthetic labeled trajectories.
`train_sft.py` handles supervised training; rollout/evaluation and research
training scripts are also retained. Released weights are in
`release/hf/model.safetensors`, with configuration and calibration metadata in
`release/hf/config.json`. Sirpi uses these weights unchanged.

## Extension points

- Natural language: extend or replace the template parser with a planner
  producing validated `Goal` objects while retaining dimension review.
- New operations: extend schema, candidates, executors, parameter resolution
  and teacher, then collect data and retrain/evaluate.
- Windows headless execution: configure a FreeCAD-compatible interpreter
  separately from the PyTorch environment.
- Product UI: extend the chat panel with structured goal editing.

Renaming the application does not expand the model's trained vocabulary or
add understanding of arbitrary prompts, drawings or unfamiliar workflows.
