"""Sirpi boundary checks that do not require a FreeCAD installation."""
import io
import json

import pytest

from sirpi.cli import main
from sirpi.demo import SocketEnv
from freecad_s1.runtime.fcenv import PROTOCOL_PREFIX


def test_cli_version(capsys):
    with pytest.raises(SystemExit) as result:
        main(["--version"])
    assert result.value.code == 0
    assert "Sirpi 0.1.0" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["--goals", "missing.json"], ["--name", "part"], ["--port", "0"], ["--delay", "-1"]])
def test_invalid_demo_input_is_rejected_before_connecting(argv):
    with pytest.raises(SystemExit) as result:
        main(["demo", *argv])
    assert result.value.code == 2


class FakeSocket:
    def sendall(self, data):
        self.sent = json.loads(data)


@pytest.mark.parametrize("reply", ["", "invalid\n", PROTOCOL_PREFIX + '{"ok":false,"error":"bad goal"}\n'])
def test_broken_server_response_is_an_error(reply):
    env = SocketEnv.__new__(SocketEnv)
    env.sock = FakeSocket()
    env.file = io.StringIO(reply)
    with pytest.raises(RuntimeError):
        env.call({"op": "score"})


def test_protocol_response_roundtrip():
    env = SocketEnv.__new__(SocketEnv)
    env.sock = FakeSocket()
    env.file = io.StringIO(PROTOCOL_PREFIX + '{"ok":true,"iou":1.0}\n')
    assert env.call({"op": "score"})["iou"] == 1
    assert env.sock.sent == {"op": "score"}


@pytest.mark.parametrize("done,match,expected", [(True, True, 0), (False, True, 1), (True, False, 1)])
def test_demo_requires_done_and_geometry_match(monkeypatch, tmp_path, done, match, expected):
    from dataclasses import asdict
    from freecad_s1.schema import Goal, GoalFeature, State
    from freecad_s1.model import net
    from freecad_s1 import rollout
    from sirpi import demo

    goal = Goal([GoalFeature("base_box", {"w": 20, "d": 10, "h": 5})], scale=20)
    state = asdict(State())

    class FakeEnv:
        closed = False

        def call(self, request):
            if request["op"] == "reset":
                return {"goal": asdict(goal), "state": state, "actions": ["Done"], "budget": 1}
            if request["op"] == "step":
                return {"state": state, "actions": [], "info": {"done": done}}
            if request["op"] == "score":
                return {"match": match, "iou": 1.0 if match else 0.5}
            if request["op"] == "save":
                return {"fcstd": request["fcstd"], "png": request["png"]}
            raise AssertionError(request)

        def close(self):
            self.closed = True

    class FakePolicy:
        def __init__(self, model, device):
            assert device == "cpu"

        def act(self, *args):
            return ["Done"]

    env = FakeEnv()
    monkeypatch.setattr(demo, "SocketEnv", lambda *args: env)
    monkeypatch.setattr(net, "from_pretrained", lambda *args, **kwargs: object())
    monkeypatch.setattr(rollout, "Policy", FakePolicy)
    assert demo.main(["--out", str(tmp_path), "--delay", "0"]) == expected
    assert env.closed
    assert json.loads((tmp_path / "result.json").read_text())["success"] == (expected == 0)
