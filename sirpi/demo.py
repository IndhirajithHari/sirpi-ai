"""CPU-driven GUI rollout, adapted from the MIT-licensed upstream GUI demo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import time

from freecad_s1.runtime.fcenv import PROTOCOL_PREFIX
from freecad_s1.schema import Goal, State
from .cli import default_model


class SocketEnv:
    def __init__(self, port: int, wait: float = 30.0) -> None:
        deadline = time.monotonic() + wait
        while True:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                self.sock.settimeout(120)
                self.file = self.sock.makefile("r", encoding="utf-8")
                return
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"Cannot reach Sirpi on port {port}. Start scripts/Sirpi.FCMacro in FreeCAD.") from exc
                time.sleep(0.25)

    def call(self, request: dict) -> dict:
        self.sock.sendall((json.dumps(request) + "\n").encode("utf-8"))
        line = self.file.readline()
        if not line.startswith(PROTOCOL_PREFIX):
            raise RuntimeError("FreeCAD disconnected or sent an invalid Sirpi response")
        response = json.loads(line[len(PROTOCOL_PREFIX):])
        if not response.get("ok"):
            raise RuntimeError(response.get("error", "FreeCAD request failed"))
        return response

    def close(self) -> None:
        self.file.close()
        self.sock.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sirpi demo", description="Build a structured goal in the FreeCAD GUI on CPU")
    parser.add_argument("--model", default=default_model())
    parser.add_argument("--level", type=int, choices=(1, 2, 3), default=3)
    parser.add_argument("--split", default="iid")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--wait", type=float, default=30)
    parser.add_argument("--out", type=Path, default=Path("runs/sirpi"))
    parser.add_argument("--goals", type=Path, help="JSON mapping of names to structured goals")
    parser.add_argument("--name", help="Name in --goals")
    args = parser.parse_args(argv)
    if bool(args.goals) != bool(args.name):
        parser.error("--goals and --name must be provided together")
    if args.delay < 0 or args.wait < 0 or not 1 <= args.port <= 65535:
        parser.error("delay/wait must be nonnegative and port must be between 1 and 65535")
    request = {"op": "reset", "level": args.level, "split": args.split, "seed": args.seed}
    if args.goals:
        goals = json.loads(args.goals.read_text(encoding="utf-8"))
        if args.name not in goals:
            parser.error(f"Unknown goal {args.name!r}. Available: {', '.join(goals)}")
        request = {"op": "reset", "goal": goals[args.name],
                   "start": {"doc_open": True, "workbench": "PartDesignWorkbench"}}

    import torch
    from freecad_s1.model.net import from_pretrained
    from freecad_s1.rollout import Policy

    torch.set_num_threads(1)
    policy = Policy(from_pretrained(args.model, device="cpu"), "cpu")
    env = SocketEnv(args.port, args.wait)
    try:
        response = env.call(request)
        goal = Goal.from_json(response["goal"])
        print("Sirpi goal:", " -> ".join(f.kind for f in goal.features))
        state, actions = State.from_json(response["state"]), response["actions"]
        done = False
        steps = 0
        for steps in range(1, response["budget"] + 1):
            if not actions:
                break
            action = policy.act([state], [goal], [actions])[0]
            print(f"{steps:3d}  {action}")
            result = env.call({"op": "step", "action": action})
            if result["info"].get("error"):
                print("FreeCAD:", result["info"]["error"])
            done = result["info"]["done"]
            if done:
                break
            state, actions = State.from_json(result["state"]), result["actions"]
            time.sleep(args.delay)
        score = env.call({"op": "score"})
        out = args.out.resolve()
        out.mkdir(parents=True, exist_ok=True)
        # Fixed basename keeps a user-supplied goal name out of filesystem paths.
        saved = env.call({"op": "save", "fcstd": str(out / "Sirpi.FCStd"),
                          "png": str(out / "Sirpi.png"), "width": 1600, "height": 1600,
                          "background": "Current"})
        success = bool(done and score["match"])
        report = {"success": success, "done": done, "steps": steps,
                  "iou": score["iou"], "saved": saved}
        (out / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if success else 1
    finally:
        env.close()
