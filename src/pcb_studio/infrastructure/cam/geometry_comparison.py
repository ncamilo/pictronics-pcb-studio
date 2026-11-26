"""Research metrics for comparing two polygonal geometries in the same mm frame."""
from dataclasses import dataclass
from math import isfinite

from shapely import get_coordinates
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from pcb_studio.domain.pcb import BoardOutline, CopperLayer


@dataclass(frozen=True)
class GeometryComparison:
    candidate_area_mm2: float
    reference_area_mm2: float
    symmetric_difference_mm2: float
    candidate_only_mm2: float
    reference_only_mm2: float
    boundary_hausdorff_mm: float
    candidate_components: int
    reference_components: int
    candidate_holes: int
    reference_holes: int
    max_bounds_delta_mm: float

    @property
    def matching_topology_counts(self):
        return (self.candidate_components == self.reference_components
                and self.candidate_holes == self.reference_holes)


def geometry_from_copper(layer: CopperLayer):
    return unary_union([Polygon(p.exterior, p.holes) for p in layer.polygons])


def geometry_from_outline(outline: BoardOutline):
    return Polygon(outline.exterior, outline.holes)


def _check(shape):
    if (not isinstance(shape, (Polygon, MultiPolygon)) or shape.is_empty
            or not shape.is_valid or shape.has_z
            or not all(isfinite(v) for point in get_coordinates(shape) for v in point)
            or not isfinite(shape.area)):
        raise ValueError("Expected nonempty valid finite XY polygonal geometry")


def _counts(shape):
    polygons = [shape] if isinstance(shape, Polygon) else list(shape.geoms)
    return len(polygons), sum(len(p.interiors) for p in polygons)


def compare_geometry(candidate, reference):
    """Measure discrepancies only; no implicit alignment or acceptance tolerance.

    Boundary Hausdorff distance is the discrete GEOS measure, not a certified
    continuous maximum error. Topology counts are necessary, not sufficient,
    for equivalent topology. Empty geometry requires a separate explicit check.
    """
    _check(candidate)
    _check(reference)
    nc, hc = _counts(candidate)
    nr, hr = _counts(reference)
    return GeometryComparison(
        candidate.area, reference.area,
        candidate.symmetric_difference(reference).area,
        candidate.difference(reference).area, reference.difference(candidate).area,
        candidate.boundary.hausdorff_distance(reference.boundary),
        nc, nr, hc, hr,
        max(abs(a-b) for a, b in zip(candidate.bounds, reference.bounds)),
    )
