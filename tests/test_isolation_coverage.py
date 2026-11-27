"""Coverage metrics, independent geometry probes, and candidate evaluation."""
import pytest
pytest.importorskip("shapely")
from shapely import from_wkb
from shapely.geometry import box, Point
from pcb_studio.infrastructure.cam.isolation_coverage import (
    measure_isolation, evaluate_tools,
)


BOARD = box(0, 0, 20, 20)


def test_area_partition():
    report = measure_isolation(box(5, 5, 10, 10), BOARD, 0.4, target_width_mm=0.4)
    assert report.covered_mm2 + report.residual_mm2 == pytest.approx(report.target_mm2)
    assert 0 < report.coverage_fraction <= 1
    assert from_wkb(report.residual_wkb_hex).area == pytest.approx(report.residual_mm2)


def test_gap_unreachable_for_wide_tool():
    copper = box(3, 3, 7, 7).union(box(7.2, 3, 11, 7))
    wide = measure_isolation(copper, BOARD, 0.4, target_width_mm=0.4)
    narrow = measure_isolation(copper, BOARD, 0.15, target_width_mm=0.4)
    assert wide.merged_passes == (0,)
    assert narrow.merged_passes == ()
    gap_center = Point(7.1, 5)
    assert from_wkb(wide.residual_wkb_hex).covers(gap_center)
    assert not from_wkb(narrow.residual_wkb_hex).covers(gap_center)
    print(f"gap case: 0.40 mm coverage={wide.coverage_fraction:.6f}, "
          f"0.15 mm coverage={narrow.coverage_fraction:.6f}; "
          f"residuals={wide.residual_mm2:.6f}, {narrow.residual_mm2:.6f} mm2")


def test_disappearing_hole():
    copper = box(5, 5, 15, 15).difference(box(9.9, 9.9, 10.1, 10.1))
    wide = measure_isolation(copper, BOARD, 0.4, target_width_mm=0.4)
    narrow = measure_isolation(copper, BOARD, 0.15, target_width_mm=0.4)
    assert wide.disappeared_hole_passes == (0,)
    assert narrow.disappeared_hole_passes == ()
    assert from_wkb(wide.residual_wkb_hex).covers(Point(10, 10))
    assert not from_wkb(narrow.residual_wkb_hex).covers(Point(10, 10))


def test_multiple_passes_increase_coverage():
    copper = box(5, 5, 10, 10)
    first = measure_isolation(copper, BOARD, 0.2, target_width_mm=0.6)
    third = measure_isolation(copper, BOARD, 0.2, target_width_mm=0.6, passes=3)
    assert third.covered_mm2 > first.covered_mm2
    assert third.residual_mm2 < first.residual_mm2


def test_candidate_rejection_and_common_target():
    copper = box(0.3, 3, 4, 7)
    results = evaluate_tools(copper, BOARD, [0.1, 0.2, 0.4], target_width_mm=0.4)
    assert results[0].coverage is not None
    assert results[1].coverage is not None
    assert results[2].coverage is None
    assert "leaves board" in results[2].rejection
    assert results[0].coverage.target_mm2 == results[1].coverage.target_mm2


@pytest.mark.parametrize("width", [0, 0.001, float("nan"), float("inf")])
def test_invalid_target(width):
    with pytest.raises(ValueError):
        measure_isolation(box(5, 5, 10, 10), BOARD, 0.4, target_width_mm=width)


def test_invalid_candidate():
    with pytest.raises(ValueError):
        evaluate_tools(box(5, 5, 10, 10), BOARD, [0], target_width_mm=0.4)
