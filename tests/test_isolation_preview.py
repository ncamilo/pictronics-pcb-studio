"""Analytic tests for experimental planar isolation geometry."""
import math
import pytest

pytest.importorskip("shapely")
from shapely.geometry import box, Polygon, LineString, LinearRing
from pcb_studio.infrastructure.cam.isolation_preview import (
    generate_isolation_preview, v_bit_diameter,
)


@pytest.mark.parametrize("tip,angle,depth,expected", [
    (0.1, 30, 0.1, 0.1 + 0.2 * math.tan(math.pi / 12)),
    (0.1, 90, 0.2, 0.5),
    (0.2, 60, 0, 0.2),
])
def test_v_bit_geometry(tip, angle, depth, expected):
    assert v_bit_diameter(tip, angle, depth) == pytest.approx(expected)


@pytest.mark.parametrize("tip,angle,depth", [
    (-0.1, 30, 0.1), (0.1, 180, 0.1), (0.1, 0, 0.1),
    (0.1, 30, -0.1), (float("nan"), 30, 0.1), (0, 30, 0),
])
def test_invalid_v_bit(tip, angle, depth):
    with pytest.raises(ValueError):
        v_bit_diameter(tip, angle, depth)


def test_three_passes_and_copper_clearance():
    copper = box(5, 5, 15, 10)
    board = box(0, 0, 20, 20)
    result = generate_isolation_preview(copper, board, 0.4, passes=3, overlap=0.25)
    assert [p.offset_mm for p in result] == pytest.approx([0.202, 0.502, 0.802])
    for p in result:
        assert len(p.paths) == 1
        path = LineString(p.paths[0])
        assert path.is_ring
        assert path.distance(copper) >= 0.2
        assert path.bounds == pytest.approx((5-p.offset_mm, 5-p.offset_mm,
                                             15+p.offset_mm, 10+p.offset_mm))
        assert not p.merged_components


def test_direction_and_internal_ring():
    copper = Polygon(box(3, 3, 17, 17).exterior.coords,
                     [box(7, 7, 13, 13).exterior.coords])
    board = box(0, 0, 20, 20)
    for clockwise in (True, False):
        [p] = generate_isolation_preview(copper, board, 0.4, clockwise=clockwise)
        assert len(p.paths) == 2
        assert LinearRing(p.paths[0]).is_ccw == (not clockwise)
        assert LinearRing(p.paths[1]).is_ccw == clockwise


def test_narrow_gap_flagged():
    copper = box(3, 3, 7, 7).union(box(7.2, 3, 11, 7))
    [p] = generate_isolation_preview(copper, box(0, 0, 20, 20), 0.4)
    assert p.merged_components
    assert len(p.paths) == 1


def test_board_edge_rejected():
    with pytest.raises(ValueError, match="leaves board"):
        generate_isolation_preview(box(0.1, 3, 4, 7), box(0, 0, 20, 20), 0.4)


def test_cutout_rejected():
    board = box(0, 0, 20, 20).difference(box(5, 5, 10, 10))
    with pytest.raises(ValueError, match="leaves board"):
        generate_isolation_preview(box(2, 5, 4.9, 10), board, 0.4)


@pytest.mark.parametrize("settings", [
    {"diameter_mm": 0}, {"diameter_mm": float("inf")},
    {"diameter_mm": 0.4, "overlap": 1},
    {"diameter_mm": 0.4, "passes": 0},
])
def test_invalid_settings(settings):
    with pytest.raises(ValueError):
        generate_isolation_preview(box(5, 5, 10, 10), box(0, 0, 20, 20), **settings)


def test_synthetic_board_integration():
    from pathlib import Path
    pytest.importorskip("gerbonara")
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    from pcb_studio.infrastructure.cam.geometry_comparison import (
        geometry_from_copper, geometry_from_outline,
    )
    folder = Path(__file__).resolve().parents[1] / "examples" / "synthetic_board"
    importer = GerbonaraImporter()
    copper = geometry_from_copper(importer.copper(folder / "bottom.gbr", "bottom"))
    board = geometry_from_outline(importer.outline(folder / "outline.gbr"))
    [p] = generate_isolation_preview(copper, board, 0.4)
    assert len(p.paths) == 1
    assert LineString(p.paths[0]).is_ring
    print(f"synthetic isolation: {len(p.paths[0])} vertices, "
          f"{LineString(p.paths[0]).length:.6f} mm centerline")
