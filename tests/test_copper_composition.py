"""Test ordered copper composition; integration limited to rectangular fixtures."""
import pytest
pytest.importorskip("shapely")
from shapely.geometry import box, LineString
from pcb_studio.infrastructure.cam.copper_composition import compose_copper


def test_clear_hole_and_redark():
    outer = box(0, 0, 10, 10)
    hole = box(2, 2, 8, 8)
    island = box(4, 4, 6, 6)
    result = compose_copper([(outer, True), (hole, False), (island, True)])
    assert result.area == pytest.approx(68)
    assert result.symmetric_difference(outer.difference(hole).union(island)).area == 0


def test_order_matters():
    large = box(0, 0, 10, 10)
    small = box(2, 2, 8, 8)
    assert compose_copper([(small, False), (large, True)]).area == 100
    assert compose_copper([(large, True), (small, False)]).area == 64


def test_reject_non_polygon():
    with pytest.raises(ValueError):
        compose_copper([(LineString([(0, 0), (1, 1)]), True)])


def test_gerber_rectangle_polarity_integration(tmp_path):
    gerbonara = pytest.importorskip("gerbonara")
    from gerbonara.utils import MM
    path = tmp_path / "polarity.gbr"
    path.write_text("%FSLAX46Y46*%\n%MOMM*%\n%ADD10R,10X10*%\n%ADD11R,6X6*%\n"
                    "%ADD12R,2X2*%\n%LPD*%\nD10*\nX5000000Y5000000D03*\n"
                    "%LPC*%\nD11*\nX5000000Y5000000D03*\n%LPD*%\nD12*\n"
                    "X5000000Y5000000D03*\nM02*\n", encoding="ascii")
    layer = gerbonara.GerberFile.open(path)
    assert len(layer.objects) == 3
    operations = []
    # Bounding boxes equal the actual geometry ONLY for these known solid,
    # axis-aligned rectangular flashes; never generalize this to other objects.
    for obj in layer.objects:
        assert type(obj).__name__ == "Flash"
        lo, hi = obj.bounding_box(unit=MM)
        operations.append((box(*lo, *hi), obj.polarity_dark))
    result = compose_copper(operations)
    expected = box(0, 0, 10, 10).difference(box(2, 2, 8, 8)).union(box(4, 4, 6, 6))
    assert result.area == pytest.approx(68)
    assert result.symmetric_difference(expected).area == pytest.approx(0)
