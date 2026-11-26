import pytest
from pcb_studio.domain.pcb import BoardOutline, CopperPolygon, Drill, PCBProject, Slot


def test_preview_never_ready():
    assert not PCBProject("demo", ()).manufacturing_ready


@pytest.mark.parametrize("point,dia", [((0, 0), 0), ((0, 0), -1), ((float("nan"), 0), 1)])
def test_invalid_drill(point, dia):
    with pytest.raises(ValueError):
        Drill(point, dia)


def test_invalid_outline():
    with pytest.raises(ValueError):
        BoardOutline("demo", ((0, 0), (1, 0), (1, 1)))


def test_invalid_slot():
    with pytest.raises(ValueError):
        Slot((1, 1), (1, 1), 0.8)


def test_polygon_retains_holes():
    ring = ((0, 0), (10, 0), (10, 10), (0, 0))
    hole = ((1, 1), (2, 1), (2, 2), (1, 1))
    assert CopperPolygon(ring, (hole,)).holes == (hole,)
