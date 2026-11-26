"""Research adapter for FlatCAM path ordering; no G-code or motion."""
from math import dist, isfinite

from pcb_studio.vendor.flatcam.path_order import order_paths, order_points


def optimize_drills(points, start=(0.0, 0.0), improve=True):
    """Return indices of drill centers, preserving duplicates."""
    def xy(point):
        point = tuple(point)
        if len(point) != 2 or not all(isfinite(v) for v in point):
            raise ValueError("Expected finite XY coordinates")
        return point

    points = [xy(point) for point in points]
    start = xy(start)
    result = order_points(points, start=start, improve=improve)
    if sorted(result) != list(range(len(points))):
        raise ValueError("Optimizer did not preserve all drill indices")
    return result


def rapid_distance(points, order, start=(0.0, 0.0)):
    """Open-route XY travel, excluding drilling and return-to-origin."""
    length = 0.0
    current = start
    for index in order:
        length += dist(current, points[index])
        current = points[index]
    return length


def optimize_reversible_paths(paths, start=(0.0, 0.0), *, allow_reverse=False):
    """Return (entry, original path) pairs for explicitly reversible 2D paths."""
    if not allow_reverse:
        raise ValueError("Direction-constrained paths require a different optimizer")
    paths = list(paths)
    if len(start) != 2 or not all(isfinite(v) for v in start):
        raise ValueError("Invalid start")
    for path in paths:
        if (getattr(path, "geom_type", None) not in ("LineString", "LinearRing")
                or path.is_empty or not path.is_valid
                or any(len(p) != 2 or not all(isfinite(v) for v in p) for p in path.coords)):
            raise ValueError("Expected nonempty, valid, finite XY paths")
    result = order_paths(paths, start=start)
    from collections import Counter
    if Counter(id(p) for _, p in result) != Counter(id(p) for p in paths):
        raise ValueError("Optimizer did not preserve paths")
    if any(entry not in (tuple(p.coords[0]), tuple(p.coords[-1])) for entry, p in result):
        raise ValueError("Invalid entry point")
    return result
