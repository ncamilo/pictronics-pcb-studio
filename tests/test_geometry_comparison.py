"""Independent metric oracles for later cross-parser comparisons."""
import pytest
pytest.importorskip("shapely")
from shapely.geometry import box, Polygon, MultiPolygon, LineString
from pcb_studio.infrastructure.cam.geometry_comparison import compare_geometry


def test_equal_geometry():
    r = compare_geometry(box(0, 0, 10, 10), box(0, 0, 10, 10))
    assert r.symmetric_difference_mm2 == 0
    assert r.boundary_hausdorff_mm == 0
    assert r.max_bounds_delta_mm == 0
    assert r.matching_topology_counts


def test_equal_area_translation_is_not_equal_geometry():
    r = compare_geometry(box(1, 0, 11, 10), box(0, 0, 10, 10))
    assert r.candidate_area_mm2 == r.reference_area_mm2 == 100
    assert r.symmetric_difference_mm2 == 20
    assert r.candidate_only_mm2 == r.reference_only_mm2 == 10
    assert r.boundary_hausdorff_mm == pytest.approx(1)
    assert r.max_bounds_delta_mm == 1


def test_missing_hole_with_same_bounds():
    outer = box(0, 0, 10, 10)
    r = compare_geometry(outer, outer.difference(box(2, 2, 8, 8)))
    assert r.symmetric_difference_mm2 == 36
    assert r.candidate_only_mm2 == 36
    assert r.reference_only_mm2 == 0
    assert r.max_bounds_delta_mm == 0
    assert not r.matching_topology_counts
    assert (r.candidate_holes, r.reference_holes) == (0, 1)


def test_disconnected_material():
    reference = MultiPolygon([box(0, 0, 1, 1), box(2, 0, 3, 1)])
    r = compare_geometry(box(0, 0, 3, 1), reference)
    assert (r.candidate_components, r.reference_components) == (1, 2)
    assert r.symmetric_difference_mm2 == 1


@pytest.mark.parametrize("bad", [Polygon(), LineString([(0, 0), (1, 1)]),
                                  Polygon([(0, 0), (2, 2), (2, 0), (0, 2)])])
def test_invalid_reference_rejected(bad):
    with pytest.raises(ValueError):
        compare_geometry(box(0, 0, 1, 1), bad)
