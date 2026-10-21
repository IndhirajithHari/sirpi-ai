"""Strict, local text-to-goal planning. No code generation or network service."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import math
import re

from freecad_s1.schema import Goal, GoalFeature

EXAMPLES = (
    "Create a plate 100 x 60 x 8 mm",
    "Create a plate 100 x 60 x 8 mm with 4 holes diameter 6 mm inset 10 mm",
    "Create a cylinder diameter 40 mm height 20 mm",
    "Create a cylinder diameter 40 mm height 20 mm with a center hole diameter 10 mm",
    "Create a ring outer diameter 60 mm inner diameter 30 mm height 10 mm",
)
NUMBER = r"(?:\d+(?:\.\d+)?|\.\d+)"
DIM = rf"({NUMBER})(?:\s*mm)?"
RECTANGLE = r"(?:plate|box|block|square|rectangle)"
SHAPE = r"(?:plate|box|block|square|rectangle|cylinder|ring)"


class RequestError(ValueError):
    """A request needs clarification or cannot be safely represented."""


@dataclass
class Plan:
    goal: Goal
    summary: str


def normalize(text: str) -> str:
    text = " ".join(text.lower().replace("×", "x").replace("*", "x").split()).rstrip(".!?")
    text = re.sub(r"\bby\b", "x", text)
    text = re.sub(r"^please\s+", "", text)
    text = re.sub(r"^(?:create|make|build)(?:\s+me)?\s+", "", text)
    text = re.sub(r"^(?:a|an)\s+", "", text)
    text = re.sub(rf"^({SHAPE})\s+(?:at|of size|size|measuring)\s+", r"\1 ", text)
    return text


def _check_request(text: str) -> None:
    if len(text) > 1000:
        raise RequestError("Please keep the request under 1000 characters.")
    # 'in' is also an English preposition; only treat it as inches after a number.
    if re.search(r"\b(?:cm|inch|inches)\b|\d\s*(?:in|m)\b|[\"']", text):
        raise RequestError("This version uses millimetres only. Convert your dimensions to mm.")


def _check_square(text: str, width: float, depth: float) -> None:
    if text.startswith("square ") and width != depth:
        raise RequestError("A square needs equal sides. Use rectangle for different width and depth.")


def _dimensions(values) -> list[float]:
    result = [float(v) for v in values]
    if any(not 0.1 <= v <= 1000 for v in result):
        raise RequestError("Use dimensions between 0.1 and 1000 mm.")
    return result


def parse_request(text: str) -> Plan:
    """Consume the entire request, rejecting unsupported trailing features."""
    _check_request(text.lower())
    text = normalize(text)
    # Accept explicit thickness after a two-dimensional rectangular outline.
    text = re.sub(rf"^({RECTANGLE}\s+{DIM}\s*x\s*{DIM})\s+(?:with\s+)?(?:a\s+)?thickness(?:\s+of)?\s+",
                  r"\1 x ", text)
    base, separator, extra = text.partition(" with ")
    plate = re.fullmatch(rf"{RECTANGLE}\s+{DIM}\s*x\s*{DIM}\s*x\s*{DIM}", base)
    cylinder = re.fullmatch(rf"cylinder\s+diameter\s+{DIM}\s+height\s+{DIM}", base)
    ring = re.fullmatch(rf"ring\s+outer diameter\s+{DIM}\s+inner diameter\s+{DIM}\s+height\s+{DIM}", base)
    if plate:
        w, d, h = _dimensions(plate.groups())
        _check_square(base, w, d)
        features = [GoalFeature("base_box", {"w": w, "d": d, "h": h})]
        summary = f"Plate: {w:g} × {d:g} × {h:g} mm (X × Y × Z)."
        scale = max(w, d, h)
    elif cylinder:
        diameter, h = _dimensions(cylinder.groups())
        features = [GoalFeature("base_cyl", {"r": diameter / 2, "h": h})]
        summary = f"Cylinder: diameter {diameter:g} mm; height {h:g} mm."
        scale = max(diameter, h)
    elif ring:
        outer, inner, h = _dimensions(ring.groups())
        if inner >= outer:
            raise RequestError("The inner diameter must be smaller than the outer diameter.")
        features = [GoalFeature("base_ring", {"ro": outer / 2, "ri": inner / 2, "h": h})]
        summary = f"Ring: outer diameter {outer:g} mm; inner diameter {inner:g} mm; height {h:g} mm."
        scale = max(outer, h)
    else:
        raise RequestError("I need a supported shape and its dimensions. Choose an example below and edit its numbers.")

    if separator:
        center = re.fullmatch(rf"(?:a\s+)?cent(?:er|re)\s+hole\s+diameter\s+{DIM}", extra)
        four = re.fullmatch(rf"(?:4|four)\s+holes\s+diameter\s+{DIM}\s+inset\s+{DIM}", extra)
        if center and (plate or cylinder):
            hole_d, = _dimensions(center.groups())
            limit = min(w, d) if plate else diameter
            if hole_d >= limit:
                raise RequestError("The hole diameter must be smaller than the base width and depth.")
            features.append(GoalFeature("hole", {"r": hole_d / 2, "x": 0, "y": 0}))
            summary += f"\nOne centered through-hole: diameter {hole_d:g} mm."
        elif four and plate:
            hole_d, inset = _dimensions(four.groups())
            radius = hole_d / 2
            if inset <= radius or inset >= min(w, d) / 2:
                raise RequestError("Hole-center inset must exceed the hole radius and be less than half the smaller plate side.")
            x, y = w / 2 - inset, d / 2 - inset
            if min(2 * x, 2 * y) <= hole_d:
                raise RequestError("The holes would touch or overlap. Reduce the inset or hole diameter.")
            for hx, hy in ((-x, -y), (x, -y), (x, y), (-x, y)):
                features.append(GoalFeature("hole", {"r": radius, "x": hx, "y": hy}))
            summary += (f"\nFour through-holes: diameter {hole_d:g} mm."
                        f"\nCenters {inset:g} mm from each adjacent edge; X = ±{x:g}, Y = ±{y:g} mm.")
        else:
            raise RequestError("Supported additions: a center hole on a plate/cylinder, or four inset holes on a plate. Other features are not supported in chat yet.")

    summary += "\nA new editable document will be created. Existing documents stay open."
    return Plan(Goal(features, level=min(3, len(features)), scale=scale), summary)


class Conversation:
    """Ask for missing dimensions without guessing the thickness of a 2D outline."""
    def __init__(self):
        self.pending_shape = None
        self.pending_dimensions = None
        self.last_built = None
        self.pending_hole = None

    def remember_success(self, plan: Plan) -> None:
        """Only completed, validated builds become the basis for follow-ups."""
        self.last_built = deepcopy(plan.goal)
        self.pending_hole = None

    def center_hole(self, size: float, measurement: str) -> Plan:
        if self.last_built is None:
            raise RequestError("Build a part successfully in this chat first, then ask to add a center hole.")
        size, = _dimensions([size])
        radius = size / 2 if measurement == "diameter" else size
        goal = deepcopy(self.last_built)
        base = goal.features[0]
        p = base.params
        if base.kind not in ("base_box", "base_cyl"):
            raise RequestError("A center hole can be added to a plate or cylinder. Rings already have an opening.")
        limit = min(p["w"], p["d"]) / 2 if base.kind == "base_box" else p["r"]
        if radius >= limit:
            raise RequestError("The hole would touch or cross the outside edge. Use a smaller diameter or radius.")
        if base.kind == "base_box":
            summary = f"Plate: {p['w']:g} × {p['d']:g} × {p['h']:g} mm."
        else:
            summary = f"Cylinder: diameter {2 * p['r']:g} mm; height {p['h']:g} mm."
        for feature in goal.features[1:]:
            q = feature.params
            if feature.kind != "hole":
                raise RequestError("This follow-up currently supports parts containing only a base and through-holes.")
            if q["x"] == 0 and q["y"] == 0:
                raise RequestError("This part already has a center hole. Start a new request to change its size.")
            if math.hypot(q["x"], q["y"]) <= q["r"] + radius:
                raise RequestError("The new hole would touch or overlap an existing hole. Use a smaller size.")
            summary += f"\nKeep through-hole: diameter {2 * q['r']:g} mm at X={q['x']:g}, Y={q['y']:g} mm."
        goal.features.append(GoalFeature("hole", {"r": radius, "x": 0, "y": 0}))
        goal.level = min(3, len(goal.features))
        summary += (f"\nAdd a centered through-hole: diameter {2 * radius:g} mm (radius {radius:g} mm)."
                    "\nBased on the last successful chat build. Build creates a revised copy; the original stays open."
                    " Manual changes made in FreeCAD are not included in this copy.")
        self.pending_hole = None
        return Plan(goal, summary)

    def follow_up(self, text: str) -> Plan | None:
        hole = re.fullmatch(
            rf"(?:now\s+)?(?:(?:add|put|make|create)\s+)?(?:a\s+)?"
            rf"(?:hole\s+(?:in|at)\s+(?:the\s+)?cent(?:er|re)|(?:cent(?:er|re)|central)\s+hole)"
            rf"(?:\s+(?:at|with|of))?(?:\s+(diameter|radius))?(?:\s+{DIM})?", text)
        if hole:
            if self.last_built is None:
                raise RequestError("Build a part successfully in this chat first, then ask to add a center hole.")
            measurement, amount = hole.groups()
            self.pending_shape = self.pending_dimensions = None
            self.pending_hole = {"amount": amount, "measurement": measurement}
            if amount is not None and measurement is not None:
                return self.center_hole(float(amount), measurement)
            if amount is not None:
                _dimensions([amount])
                raise RequestError(f"Does {float(amount):g} mm mean the hole diameter or radius? Reply diameter or radius.")
            raise RequestError("What hole size? Reply with diameter 1 mm or radius 0.5 mm.")
        if self.pending_hole is not None:
            answer = re.fullmatch(rf"(diameter|radius)(?:\s+{DIM})?", text)
            if answer:
                measurement, amount = answer.groups()
                amount = amount or self.pending_hole["amount"]
                if amount is None:
                    raise RequestError("Please include a size, for example: diameter 1 mm.")
                return self.center_hole(float(amount), measurement)
            raise RequestError("Please clarify the hole size, for example: diameter 1 mm. Or start a new request with a shape name.")
        if re.match(r"(?:now\s+)?(?:add|put)\b", text):
            raise RequestError("Supported follow-up: add a center hole diameter 1 mm. Other edits are not supported yet.")
        return None

    def submit(self, text: str) -> Plan:
        _check_request(text.lower())
        normalized = normalize(text)
        if re.match(rf"{SHAPE}\b", normalized):
            self.pending_hole = None
        else:
            follow_up = self.follow_up(normalized)
            if follow_up is not None:
                return follow_up
        if re.fullmatch(SHAPE, normalized):
            self.pending_shape = normalized
            self.pending_dimensions = None
            if re.fullmatch(RECTANGLE, normalized):
                raise RequestError("What width, depth and thickness in mm? Reply like: 100 x 60 x 8 mm")
            if normalized == "cylinder":
                raise RequestError("What diameter and height in mm? Reply like: diameter 40 mm height 20 mm")
            raise RequestError("What outer diameter, inner diameter and height in mm? Reply like: outer diameter 60 mm inner diameter 30 mm height 10 mm")
        candidate = normalized
        if self.pending_shape and not re.match(rf"{SHAPE}\b", normalized):
            if self.pending_dimensions:
                thickness = re.fullmatch(rf"(?:(?:thickness|height)(?:\s+of)?\s+)?{DIM}", normalized)
                if thickness:
                    w, d = self.pending_dimensions
                    candidate = f"{self.pending_shape} {w:g} x {d:g} x {thickness.group(1)} mm"
                else:
                    raise RequestError("Please give the thickness in mm, for example: 0.5 mm. Or start a new request with a shape name.")
            else:
                candidate = self.pending_shape + " " + normalized
        outline = re.fullmatch(rf"({RECTANGLE})\s+{DIM}\s*x\s*{DIM}", candidate)
        if outline:
            w, d = _dimensions(outline.groups()[1:])
            _check_square(candidate, w, d)
            self.pending_shape = outline.group(1)
            self.pending_dimensions = (w, d)
            raise RequestError(f"I read a {w:g} × {d:g} mm outline. To make a solid part, what thickness should it have? Reply with a thickness, for example: 0.5 mm.")
        plan = parse_request(candidate)
        self.pending_shape = None
        self.pending_dimensions = None
        return plan
