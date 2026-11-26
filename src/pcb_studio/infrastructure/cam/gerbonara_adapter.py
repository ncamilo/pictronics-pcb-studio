"""Restricted experimental import adapter, not a manufacturing validator."""
import math
import warnings
from pathlib import Path

from gerbonara import ExcellonFile, GerberFile
from gerbonara.utils import MM
from shapely import affinity
from shapely.errors import GEOSException
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge

from pcb_studio.domain.pcb import (
    BoardOutline, CopperLayer, CopperPolygon, Drill, DrillLayer, Slot,
)
from pcb_studio.ports.pcb_import import PCBImportError
from pcb_studio.infrastructure.cam.copper_composition import compose_copper

# Fixed preview resolution, not a certified machining tolerance.
QUAD_SEGS = 64


def _load(file_type, path):
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            layer = file_type.open(path)
        if caught:
            raise PCBImportError("Parser warning: " + str(caught[0].message))
        if not layer.objects:
            raise PCBImportError("No graphic objects")
        return layer
    except PCBImportError:
        raise
    except Exception as exc:
        raise PCBImportError(f"Cannot parse {Path(path).name}: {exc}") from exc


def _name(obj):
    return type(obj).__name__


def _point(obj, x, y):
    return (obj.unit.convert_to(MM, getattr(obj, x)),
            obj.unit.convert_to(MM, getattr(obj, y)))


def _solid_aperture(obj, allowed):
    aperture = obj.aperture
    if _name(aperture) not in allowed or getattr(aperture, "hole_dia", None):
        raise PCBImportError("Unsupported aperture or aperture hole")
    return aperture


def _arc_centerline(p):
    """Sample a circular primitive in mm, keeping its exact endpoints."""
    start, end, center = (p.x1, p.y1), (p.x2, p.y2), (p.cx, p.cy)
    if not all(math.isfinite(v) for pt in (start, end, center) for v in pt):
        raise PCBImportError("Non-finite arc coordinates")
    radius = math.dist(start, center)
    if radius <= 0 or abs(radius - math.dist(end, center)) > 1e-5:
        raise PCBImportError("Inconsistent arc radii")
    a = math.atan2(start[1] - center[1], start[0] - center[0])
    b = math.atan2(end[1] - center[1], end[0] - center[0])
    direction = -1 if p.clockwise else 1
    sweep = math.tau if start == end else ((b - a) * direction) % math.tau
    if sweep == 0:
        raise PCBImportError("Ambiguous arc sweep")
    # Chord sagitta <= 0.001 mm, except for the separate endpoint tolerance.
    # Stable formula for 2*acos(1-tolerance/radius).
    step = min(math.pi / 32, 4 * math.asin(math.sqrt(min(1.0, 0.001 / (2 * radius)))))
    if step <= 0:
        raise PCBImportError("Arc exceeds preview precision")
    count = max(2, math.ceil(sweep / step))
    if count > 100_000:
        raise PCBImportError("Arc exceeds preview segment limit")
    points = [start]
    for i in range(1, count):
        angle = a + direction * sweep * i / count
        points.append((center[0] + radius * math.cos(angle),
                       center[1] + radius * math.sin(angle)))
    points.append(end)
    return LineString(points)


def _primitive_geometry(p):
    kind = _name(p)
    if kind == "Circle" and p.r > 0:
        return Point(p.x, p.y).buffer(p.r, quad_segs=QUAD_SEGS)
    if kind == "Line" and p.width > 0:
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(
            p.width / 2, quad_segs=QUAD_SEGS)
    if kind == "Arc" and math.isfinite(p.width) and p.width > 0:
        return _arc_centerline(p).buffer(p.width / 2, quad_segs=QUAD_SEGS)
    if kind == "Rectangle" and p.w > 0 and p.h > 0:
        shape = box(p.x-p.w/2, p.y-p.h/2, p.x+p.w/2, p.y+p.h/2)
        return affinity.rotate(shape, p.rotation, origin=(p.x, p.y), use_radians=True)
    if kind == "ArcPoly" and not any(p.arc_centers):
        return Polygon(p.outline)
    raise PCBImportError(f"Unsupported graphic primitive: {kind}")


def _ring(coords):
    return tuple((float(x), float(y)) for x, y in coords)


class GerbonaraImporter:
    """Import an explicit, limited subset without mirroring or recentering."""

    def copper(self, path, side):
        layer = _load(GerberFile, path)
        try:
            operations = []
            for obj in layer.objects:
                kind = _name(obj)
                if kind == "Flash":
                    _solid_aperture(obj, {"CircleAperture", "RectangleAperture", "ObroundAperture"})
                elif kind in ("Line", "Arc"):
                    _solid_aperture(obj, {"CircleAperture"})
                elif kind != "Region":
                    raise PCBImportError(f"Unsupported copper object: {kind}")
                primitives = list(obj.to_primitives(unit=MM))
                if len(primitives) != 1:
                    raise PCBImportError("Multiple primitives not supported in this preview")
                p = primitives[0]
                if p.polarity_dark != obj.polarity_dark:
                    raise PCBImportError("Unexpected primitive polarity")
                operations.append((_primitive_geometry(p), bool(obj.polarity_dark)))
            shape = compose_copper(operations)
            polygons = [] if shape.is_empty else (
                [shape] if shape.geom_type == "Polygon" else list(shape.geoms))
            return CopperLayer(str(path), side, tuple(
                CopperPolygon(_ring(p.exterior.coords), tuple(_ring(h.coords) for h in p.interiors))
                for p in polygons))
        except PCBImportError:
            raise
        except (ValueError, TypeError, GEOSException) as exc:
            raise PCBImportError(str(exc)) from exc

    def drills(self, path):
        layer = _load(ExcellonFile, path)
        drills, slots = [], []
        for obj in layer.objects:
            tool = _solid_aperture(obj, {"ExcellonTool"})
            dia = tool.unit.convert_to(MM, tool.diameter)
            plated = tool.plated
            kind = _name(obj)
            try:
                if kind == "Flash":
                    drills.append(Drill(_point(obj, "x", "y"), dia, plated))
                elif kind == "Line":
                    slots.append(Slot(_point(obj, "x1", "y1"), _point(obj, "x2", "y2"), dia, plated))
                else:
                    raise PCBImportError(f"Unsupported drill object: {kind}")
            except ValueError as exc:
                raise PCBImportError(str(exc)) from exc
        return DrillLayer(str(path), tuple(drills), tuple(slots))

    def outline(self, path):
        layer = _load(GerberFile, path)
        segments = []
        for obj in layer.objects:
            if _name(obj) != "Line" or not obj.polarity_dark:
                raise PCBImportError("Only dark straight outline segments are supported")
            _solid_aperture(obj, {"CircleAperture"})
            start, end = _point(obj, "x1", "y1"), _point(obj, "x2", "y2")
            if start == end or not all(math.isfinite(v) for pt in (start, end) for v in pt):
                raise PCBImportError("Invalid outline segment")
            segments.append(LineString([start, end]))
        merged = linemerge(segments)
        if merged.geom_type != "LineString" or not merged.is_ring:
            raise PCBImportError("Expected exactly one closed simple outline")
        polygon = Polygon(merged.coords)
        if not polygon.is_valid or polygon.area <= 0:
            raise PCBImportError("Invalid outline")
        return BoardOutline(str(path), _ring(merged.coords))
