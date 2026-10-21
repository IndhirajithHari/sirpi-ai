"""Text planning boundaries, dimensions and multi-turn clarification."""
import pytest

from sirpi.chat import Conversation, EXAMPLES, RequestError, parse_request


@pytest.mark.parametrize("text", EXAMPLES)
def test_examples_are_complete_goals(text):
    plan = parse_request(text)
    assert plan.goal.scale > 0
    assert plan.goal.features[0].kind.startswith("base_")


def test_four_holes_have_explicit_corner_positions():
    plan = parse_request(EXAMPLES[1])
    assert plan.goal.features[0].params == {"w": 100, "d": 60, "h": 8}
    holes = plan.goal.features[1:]
    assert len(holes) == 4
    assert {(h.params["x"], h.params["y"]) for h in holes} == {(-40, -20), (40, -20), (40, 20), (-40, 20)}
    assert all(h.params["r"] == 3 for h in holes)


def test_diameters_become_radii():
    plan = parse_request(EXAMPLES[3])
    assert plan.goal.features[0].params == {"r": 20, "h": 20}
    assert plan.goal.features[1].params == {"r": 5, "x": 0, "y": 0}
    ring = parse_request(EXAMPLES[4])
    assert ring.goal.features[0].params == {"ro": 30, "ri": 15, "h": 10}


def test_polite_unicode_decimal_input():
    plan = parse_request("Please make me a plate 40.5 × 30 × 5 mm.")
    assert plan.goal.features[0].params == {"w": 40.5, "d": 30, "h": 5}


@pytest.mark.parametrize("text", [
    "plate 0 x 20 x 5", "plate -20 x 20 x 5", "plate 1001 x 20 x 5",
    "plate nan x 20 x 5", "plate 40 x 20 x 5 cm", "plate 40 x 20 x 5 inches",
    "plate 40 x 20 x 5 mm with fillet radius 2 mm",
    "plate 40 x 20 x 5 mm and a gear", "plate 40 x 20 x 5 mm with",
    "plate 40 x 20 x 5 with a center hole diameter 20",
    "plate 40 x 20 x 5 with 4 holes diameter 6 inset 2",
    "plate 40 x 20 x 5 with 4 holes diameter 6 inset 10",
    "plate 40 x 20 x 5 with 4 holes diameter 6 inset 8",
    "ring outer diameter 30 inner diameter 30 height 10",
    "ring outer diameter 30 inner diameter 40 height 10",
    "ring outer diameter 60 inner diameter 30 height 10 with a center hole diameter 5",
    "cylinder diameter 40 height 20 with a center hole diameter 40",
    "make a gear", "import os; os.remove('file')", "x" * 1001,
])
def test_unsupported_or_invalid_requests_never_produce_a_plan(text):
    with pytest.raises(RequestError):
        parse_request(text)


@pytest.mark.parametrize("shape,dimensions,kind", [
    ("plate", "100 x 60 x 8 mm", "base_box"),
    ("cylinder", "diameter 40 mm height 20 mm", "base_cyl"),
    ("ring", "outer diameter 60 mm inner diameter 30 mm height 10 mm", "base_ring"),
])
def test_missing_dimensions_can_be_supplied_in_next_message(shape, dimensions, kind):
    conversation = Conversation()
    with pytest.raises(RequestError, match="What"):
        conversation.submit("Create a " + shape)
    assert conversation.submit(dimensions).goal.features[0].kind == kind
    assert conversation.pending_shape is None


def test_new_shape_replaces_pending_clarification():
    conversation = Conversation()
    with pytest.raises(RequestError):
        conversation.submit("plate")
    with pytest.raises(RequestError):
        conversation.submit("too large")
    assert conversation.submit(EXAMPLES[2]).goal.features[0].kind == "base_cyl"


@pytest.mark.parametrize("prompt", ["make a square at 2*2mm", "make a square 2 by 2 mm", "square 2 × 2 mm", "plate 2x2"])
def test_square_outline_asks_for_thickness_then_builds(prompt):
    conversation = Conversation()
    with pytest.raises(RequestError, match="what thickness"):
        conversation.submit(prompt)
    plan = conversation.submit("0.5 mm")
    assert plan.goal.features[0].params == {"w": 2, "d": 2, "h": 0.5}
    assert conversation.pending_dimensions is None


@pytest.mark.parametrize("prompt", ["square 2*2*0.5mm", "square 2x2 mm with thickness 0.5 mm", "square 2x2 thickness of 0.5 mm"])
def test_square_with_explicit_thickness(prompt):
    assert parse_request(prompt).goal.features[0].params == {"w": 2, "d": 2, "h": 0.5}


def test_square_clarification_does_not_accept_wrong_units_or_dimensions():
    conversation = Conversation()
    with pytest.raises(RequestError):
        conversation.submit("make a square at 2*2mm")
    for text in ("0", "-1", "1001", "0.5 cm", "0.5in", "0.5 mm with a gear"):
        with pytest.raises(RequestError):
            conversation.submit(text)
    assert conversation.submit("thickness 0.5mm").goal.features[0].params["h"] == 0.5


def test_two_dimensional_square_requires_equal_sides():
    with pytest.raises(RequestError, match="equal sides"):
        Conversation().submit("square 2*3mm")
    with pytest.raises(RequestError, match="equal sides"):
        parse_request("square 2*3*1mm")


def test_new_request_replaces_pending_square_dimensions():
    conversation = Conversation()
    with pytest.raises(RequestError):
        conversation.submit("square 2*2mm")
    assert conversation.submit(EXAMPLES[2]).goal.features[0].kind == "base_cyl"
    assert conversation.pending_dimensions is None


def test_bare_square_then_size_then_thickness():
    conversation = Conversation()
    for text in ("make a square", "2*2mm"):
        with pytest.raises(RequestError):
            conversation.submit(text)
    assert conversation.submit("1 mm").goal.features[0].params == {"w": 2, "d": 2, "h": 1}


def test_english_in_is_not_reported_as_inches():
    with pytest.raises(RequestError) as error:
        parse_request("put a hole in centre at 10 mm")
    assert "millimetres only" not in str(error.value)


def built_square():
    conversation = Conversation()
    conversation.remember_success(parse_request("square 2x2x0.5mm"))
    return conversation


def test_exact_center_hole_followup_clarifies_and_preserves_base():
    conversation = built_square()
    with pytest.raises(RequestError, match="diameter or radius"):
        conversation.submit("now add a hole in centre at 1mm")
    plan = conversation.submit("diameter")
    assert plan.goal.features[0].params == {"w": 2, "d": 2, "h": 0.5}
    assert plan.goal.features[1].params == {"r": 0.5, "x": 0, "y": 0}
    assert len(conversation.last_built.features) == 1


@pytest.mark.parametrize("text", ["add a center hole diameter 1mm", "now put a hole in the centre with diameter 1 mm", "make a centre hole radius 0.5 mm"])
def test_explicit_followup_hole_size(text):
    assert built_square().submit(text).goal.features[1].params["r"] == 0.5


def test_followup_needs_successful_build_not_just_a_review():
    conversation = Conversation()
    conversation.submit("square 2x2x0.5mm")
    with pytest.raises(RequestError, match="successfully"):
        conversation.submit("add a center hole diameter 1mm")


def test_followup_uses_last_built_not_an_unbuilt_new_review():
    conversation = built_square()
    conversation.submit("plate 100x60x8mm")
    assert conversation.submit("add a center hole diameter 1mm").goal.features[0].params["w"] == 2


def test_hole_radius_that_reaches_edge_is_rejected_and_can_be_corrected():
    conversation = built_square()
    with pytest.raises(RequestError):
        conversation.submit("now add a hole in centre at 1mm")
    with pytest.raises(RequestError, match="outside edge"):
        conversation.submit("radius")
    assert conversation.submit("diameter").goal.features[1].params["r"] == 0.5


def test_new_shape_clears_hole_clarification():
    conversation = built_square()
    with pytest.raises(RequestError):
        conversation.submit("add a centre hole")
    assert conversation.submit(EXAMPLES[2]).goal.features[0].kind == "base_cyl"
    assert conversation.pending_hole is None


def test_existing_holes_preserved_and_overlap_rejected():
    conversation = Conversation()
    conversation.remember_success(parse_request(EXAMPLES[1]))
    assert len(conversation.submit("add a center hole diameter 10mm").goal.features) == 6
    conversation.remember_success(parse_request("plate 20x20x5 with 4 holes diameter 2 inset 5"))
    with pytest.raises(RequestError, match="overlap"):
        conversation.submit("add a center hole diameter 13mm")


def test_duplicate_center_hole_rejected():
    conversation = built_square()
    conversation.remember_success(conversation.submit("add a center hole diameter 1mm"))
    with pytest.raises(RequestError, match="already"):
        conversation.submit("add a center hole diameter 0.5mm")


@pytest.mark.parametrize("text", ["add a center hole diameter 1mm and a fillet", "add a hole in centre at 1cm", "add a center hole radius -1", "now add a gear"])
def test_invalid_followups_not_silently_partially_applied(text):
    with pytest.raises(RequestError):
        built_square().submit(text)
