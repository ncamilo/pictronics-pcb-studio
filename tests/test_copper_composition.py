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


def test_batched_polarities_against_sequential():
    from shapely.geometry import GeometryCollection, Point
    from shapely import get_num_geometries
    operations=[]
    for i in range(6):
        operations.extend((Point(i*3+j*0.4,0).buffer(0.7),True) for j in range(6))
    operations.extend((box(i*3-0.1,-0.2,i*3+0.1,0.2),False) for i in range(6))
    operations.extend((box(i*3-0.05,-0.05,i*3+0.05,0.05),True) for i in range(6))
    expected=GeometryCollection()
    for g,dark in operations:
        expected=expected.union(g) if dark else expected.difference(g)
    actual=compose_copper(iter(operations))
    assert actual.is_valid
    assert actual.symmetric_difference(expected).area<1e-10
    assert get_num_geometries(actual)==get_num_geometries(expected)


def test_batch_boundary_and_invalid_late_input(monkeypatch):
    import pcb_studio.infrastructure.cam.copper_composition as module
    monkeypatch.setattr(module,"BATCH_SIZE",2)
    ops=[(box(i,0,i+2,2),True) for i in range(5)]
    ops += [(box(1,0,2,2),False),(box(3,0,4,2),False),(box(5,0,6,2),False)]
    ops += [(box(1,0,2,2),True)]
    assert compose_copper(ops).area==8
    with pytest.raises(ValueError):
        compose_copper(ops+[(LineString([(0,0),(1,1)]),True)])
