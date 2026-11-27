"""Experimental XY isolation contours, not executable toolpaths.

Inspired by FlatCAM Evo IsolationGen.py at c948622f6b906f9910990d7bafbfb3012be21350.
Independent implementation using Shapely; no upstream source copied.
"""
from dataclasses import dataclass
from math import isfinite, radians, tan

from shapely import get_coordinates
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


@dataclass(frozen=True)
class IsolationPass:
    index: int
    offset_mm: float
    paths: tuple[tuple[tuple[float, float], ...], ...]
    merged_components: bool


def v_bit_diameter(tip_mm, angle_deg, depth_mm):
    """Ideal conical tool geometry; depth is a nonnegative magnitude."""
    if (not all(isfinite(v) for v in (tip_mm, angle_deg, depth_mm))
            or tip_mm < 0 or depth_mm < 0 or not 0 < angle_deg < 180):
        raise ValueError("Invalid V-bit geometry")
    diameter = tip_mm + 2 * depth_mm * tan(radians(angle_deg / 2))
    if not isfinite(diameter) or diameter <= 0:
        raise ValueError("Invalid effective diameter")
    return diameter


def _polygonal(shape):
    if (not isinstance(shape, (Polygon, MultiPolygon)) or shape.is_empty
            or not shape.is_valid or shape.has_z
            or not all(isfinite(v) for pt in get_coordinates(shape) for v in pt)
            or not isfinite(shape.area)):
        raise ValueError("Expected valid finite XY copper or board polygon")
    return [shape] if isinstance(shape, Polygon) else list(shape.geoms)


def generate_isolation_preview(copper, board, diameter_mm, *, passes=1,
                               overlap=0.2, clearance_mm=0.002, clockwise=True):
    """Generate closed contours with conservative extra copper clearance.

    No clipping, implicit mirroring, motion, tool ordering or G-code.
    Reject a pass whose approximate swept disk leaves the board or touches copper.
    Merged contours are explicitly flagged: they may leave unisolated gaps.
    The caller must not interpret a result as complete isolation or safe machining.
    """
    original = _polygonal(copper)
    _polygonal(board)
    if (not all(isfinite(v) for v in (diameter_mm, overlap, clearance_mm))
            or diameter_mm <= 0 or not 0 <= overlap < 1 or clearance_mm <= 0
            or type(passes) is not int or not 1 <= passes <= 100
            or type(clockwise) is not bool):
        raise ValueError("Invalid isolation settings")
    if not board.covers(copper):
        raise ValueError("Copper outside board material")
    radius = diameter_mm / 2
    # Buffer polygons are approximations. Inflate the swept radius so its
    # 64-segment-per-quadrant circular chords contain the ideal disk.
    from math import cos, pi
    swept_radius = radius / cos(pi / 256)
    results = []
    for i in range(passes):
        offset = radius + clearance_mm + i * diameter_mm * (1 - overlap)
        envelope = copper.buffer(offset, quad_segs=64)
        polygons = _polygonal(envelope)
        paths = []
        for poly in polygons:
            ordered = orient(poly, sign=-1.0 if clockwise else 1.0)
            for ring in (ordered.exterior, *ordered.interiors):
                paths.append(tuple((float(x), float(y)) for x, y in ring.coords))
        swept = unary_union([LineString(path).buffer(swept_radius, quad_segs=64)
                             for path in paths])
        if not swept.disjoint(copper):
            raise ValueError("Preview swept tool intersects copper")
        if not board.covers(swept):
            raise ValueError("Preview swept tool leaves board material")
        results.append(IsolationPass(i, offset, tuple(paths), len(polygons) < len(original)))
    return tuple(results)
