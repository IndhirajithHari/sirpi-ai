"""Lightweight entry point; diagnostics work without PyTorch or FreeCAD."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys

from . import __version__

ROOT = Path(__file__).resolve().parents[1]


def default_model() -> str:
    local = ROOT / "release" / "hf"
    return str(local) if (local / "model.safetensors").is_file() else "shhivv/taiga-s1"


def find_freecad() -> str | None:
    override = os.environ.get("SIRPI_FREECAD")
    if override:
        return override if Path(override).is_file() else None
    executable = shutil.which("FreeCAD") or shutil.which("FreeCAD.exe")
    if executable:
        return executable
    for base in (os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if base:
            for pattern in ("FreeCAD*/bin/FreeCAD.exe", "Programs/FreeCAD*/bin/FreeCAD.exe"):
                matches = sorted(Path(base).glob(pattern), reverse=True)
                if matches:
                    return str(matches[0])
    app = Path("/Applications/FreeCAD.app/Contents/MacOS/FreeCAD")
    return str(app) if app.is_file() else None


def doctor() -> int:
    dependencies = {name: importlib.util.find_spec(name) is not None
                    for name in ("torch", "numpy", "safetensors", "huggingface_hub")}
    executable = find_freecad()
    print(json.dumps({"name": "Sirpi", "version": __version__, "python": sys.version.split()[0],
                      "dependencies": dependencies, "freecad_gui": executable,
                      "model": default_model(),
                      "local_weights": (ROOT / "release/hf/model.safetensors").is_file()}, indent=2))
    if not executable:
        print("FreeCAD GUI was not found. Install FreeCAD or set SIRPI_FREECAD to FreeCAD.exe.")
    return 0 if all(dependencies.values()) and executable else 1


def smoke(model_path: str) -> int:
    import random
    import torch
    from freecad_s1.actions import enumerate_actions
    from freecad_s1.goals import sample_goal
    from freecad_s1.model.net import from_pretrained, parameter_count
    from freecad_s1.rollout import Policy
    from freecad_s1.schema import State

    torch.set_num_threads(1)
    model = from_pretrained(model_path, device="cpu")
    state = State()
    goal = sample_goal(1, random.Random(7))
    actions = enumerate_actions(state)
    scores = Policy(model, "cpu").score(state, goal, actions)
    if set(scores) != set(actions) or not all(math.isfinite(p) and p >= 0 for p in scores.values()):
        raise RuntimeError("Model returned invalid action probabilities")
    if not math.isclose(sum(scores.values()), 1.0, abs_tol=1e-5):
        raise RuntimeError("Action probabilities do not sum to one")
    print(json.dumps({"name": "Sirpi", "device": "cpu", "parameters": parameter_count(model),
                      "next_action": next(iter(scores)), "probabilities": scores,
                      "check": "CPU inference only; no CAD geometry was built"}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sirpi", description="Sirpi - local CPU modeling agent for FreeCAD")
    parser.add_argument("--version", action="version", version=f"Sirpi {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check dependencies, weights and FreeCAD discovery")
    check = sub.add_parser("smoke", help="Load weights and score commands on CPU without FreeCAD")
    check.add_argument("--model", default=default_model())
    sub.add_parser("demo", help="Drive an open FreeCAD Sirpi macro session", add_help=False)
    args, rest = parser.parse_known_args(argv)
    if args.command != "demo" and rest:
        parser.error("unrecognized arguments: " + " ".join(rest))
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "smoke":
            return smoke(args.model)
        from .demo import main as demo_main
        return demo_main(rest)
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        print(f"Sirpi: {exc}", file=sys.stderr)
        return 1
