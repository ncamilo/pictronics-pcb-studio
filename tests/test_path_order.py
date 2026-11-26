"""Independent tests of experimental path-order adapter."""
from random import Random
from time import perf_counter

import pytest
pytest.importorskip("numpy")
pytest.importorskip("shapely")
from shapely.geometry import LineString
from pcb_studio.infrastructure.cam.path_optimizer import (
    optimize_drills, optimize_reversible_paths, rapid_distance,
)


def test_grid_reduces_rapid_travel():
    points = [(x * 10, y * 10) for x in range(8) for y in range(8)]
    Random(17).shuffle(points)
    order = optimize_drills(points)
    before = rapid_distance(points, range(len(points)))
    after = rapid_distance(points, order)
    print(f"grid: {before:.3f} -> {after:.3f} mm; reduction={(1-after/before)*100:.2f}%")
    assert after < before
    assert order == optimize_drills(points)


def test_improvement_does_not_increase_nearest_neighbor_distance():
    rng = Random(41)
    points = [(rng.uniform(0, 200), rng.uniform(0, 150)) for _ in range(200)]
    nearest = optimize_drills(points, improve=False)
    improved = optimize_drills(points)
    assert rapid_distance(points, improved) <= rapid_distance(points, nearest) + 1e-8


def test_duplicate_and_empty_points():
    points = [(1, 2), (1, 2), (3, 4)]
    assert sorted(optimize_drills(points)) == [0, 1, 2]
    assert optimize_drills([]) == []


@pytest.mark.parametrize("point", [(float("nan"), 0), (1, 2, 3), (float("inf"), 0)])
def test_reject_invalid_points(point):
    with pytest.raises(ValueError):
        optimize_drills([point])


def test_reverse_only_when_allowed():
    path = LineString([(10, 0), (1, 0)])
    with pytest.raises(ValueError):
        optimize_reversible_paths([path])
    [(entry, original)] = optimize_reversible_paths([path], allow_reverse=True)
    assert entry == (1, 0)
    assert original is path
    assert list(path.coords) == [(10, 0), (1, 0)]


def test_reversible_paths_preserve_geometry_and_multiplicity():
    a = LineString([(10, 0), (15, 0)])
    b = LineString([(2, 0), (3, 0)])
    paths = [a, b, a]
    result = optimize_reversible_paths(paths, allow_reverse=True)
    assert sorted(id(p) for _, p in result) == sorted(id(p) for p in paths)
    assert all(entry in (tuple(p.coords[0]), tuple(p.coords[-1])) for entry, p in result)


def test_reject_empty_path():
    with pytest.raises(ValueError):
        optimize_reversible_paths([LineString()], allow_reverse=True)


def test_1000_drill_benchmark():
    rng = Random(2026)
    points = [(rng.uniform(0, 200), rng.uniform(0, 150)) for _ in range(1000)]
    start = perf_counter()
    order = optimize_drills(points)
    elapsed = perf_counter() - start
    before = rapid_distance(points, range(len(points)))
    after = rapid_distance(points, order)
    print(f"1000 drills: {before:.3f} -> {after:.3f} mm; {elapsed:.4f} s")
    assert sorted(order) == list(range(1000))
    assert after < before
