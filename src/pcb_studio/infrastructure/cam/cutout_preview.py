"""Planar board cutout preview. No executable motion or depth instructions."""
from dataclasses import dataclass
from math import isfinite, isclose

from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import substring, unary_union

from pcb_studio.domain.pcb import BoardOutline, PanelOutline, validate_xy
from pcb_studio.infrastructure.cam.geometry_comparison import geometry_from_outline
from pcb_studio.infrastructure.cam.isolation_preview import _polygonal

XY = tuple[float, float]
PathXY = tuple[XY, ...]


@dataclass(frozen=True)
class Tab:
    anchor: XY
    width_mm: float

    def __post_init__(self):
        validate_xy(self.anchor)
        if not isfinite(self.width_mm) or self.width_mm <= 0:
            raise ValueError("Invalid tab width")


@dataclass(frozen=True)
class CutoutPreview:
    internal_paths: tuple[PathXY, ...]
    exterior_paths: tuple[PathXY, ...]
    tab_gaps: tuple[PathXY, ...]
    diameter_mm: float
    offset_mm: float
    exterior_full_length_mm: float

    @property
    def manufacturing_ready(self):
        return False


def _xy(line):
    return tuple((float(x), float(y)) for x, y in line.coords)


def _cyclic_part(line, start, end):
    length = line.length
    start %= length
    span = end
    # end is a positive travel length, not an absolute station.
    if start + span <= length:
        return substring(line, start, start + span)
    a = substring(line, start, length)
    b = substring(line, 0, start + span - length)
    return LineString([*a.coords, *list(b.coords)[1:]])


def plan_cutout_preview(outline: BoardOutline, stock: BoardOutline, diameter_mm,
                        *, tabs=(), margin_mm=0.002, clockwise=True):
    """Compensate canonical edge centerlines, then remove straight tab gaps.

    Tab anchors must be on the original exterior and project to a straight
    portion of the compensated contour. A gap is width + cutter diameter.
    Width is nominal along that straight line, not a mechanical strength
    guarantee. All internal contours precede the exterior. No automatic
    clipping, nesting, slug retention, depth planning or tool activation.
    """
    if (not all(isfinite(v) for v in (diameter_mm, margin_mm))
            or diameter_mm <= 0 or margin_mm <= 0 or type(clockwise) is not bool):
        raise ValueError("Invalid cutout settings")
    if isinstance(outline, PanelOutline):
        return _panel_cutout(outline, stock, diameter_mm, tuple(tabs), margin_mm, clockwise)
    board, stock_shape = map(geometry_from_outline, (outline, stock))
    _polygonal(board)
    _polygonal(stock_shape)
    if not stock_shape.covers(board):
        raise ValueError("Board outside stock")
    radius = diameter_mm / 2
    offset = radius + margin_mm
    sign = -1.0 if clockwise else 1.0
    outer = Polygon(board.exterior).buffer(offset, quad_segs=64)
    if not isinstance(outer, Polygon) or outer.is_empty or not outer.is_valid or outer.interiors:
        raise ValueError("Unsupported compensated exterior topology")
    exterior = LineString(orient(outer, sign=sign).exterior.coords)
    inner_paths = []
    for ring in board.interiors:
        inset = Polygon(ring).buffer(-offset, quad_segs=64)
        if not isinstance(inset, Polygon) or inset.is_empty or not inset.is_valid or inset.interiors:
            raise ValueError("Internal cutout too small or splits at tool offset")
        inner_paths.append(LineString(orient(inset, sign=-sign).exterior.coords))
    length = exterior.length
    intervals = []
    gap_paths = []
    for tab in tabs:
        if not isinstance(tab, Tab):
            raise ValueError("Expected Tab")
        anchor = Point(tab.anchor)
        if board.exterior.distance(anchor) > 1e-8:
            raise ValueError("Tab anchor must lie on board exterior")
        center = exterior.project(anchor)
        gap = tab.width_mm + diameter_mm
        if gap >= length:
            raise ValueError("Tab gap exceeds contour length")
        start = (center - gap / 2) % length
        part = _cyclic_part(exterior, start, gap)
        if not isclose(part.length, gap, rel_tol=0, abs_tol=1e-8):
            raise ValueError("Tab gap length mismatch")
        if not isclose(Point(part.coords[0]).distance(Point(part.coords[-1])),
                       gap, rel_tol=0, abs_tol=1e-8):
            raise ValueError("Tab must lie on a straight compensated edge")
        intervals.append((start, gap, tab.width_mm, exterior.interpolate(center)))
        gap_paths.append(part)
    intervals.sort(key=lambda t: t[0])
    exterior_paths = []
    if not intervals:
        exterior_paths.append(exterior)
    else:
        for i, (start, gap, _, _) in enumerate(intervals):
            next_start = intervals[(i+1) % len(intervals)][0]
            if i == len(intervals)-1:
                next_start += length
            span = next_start - start - gap
            if span <= 1e-8:
                raise ValueError("Tab gaps overlap or touch")
            exterior_paths.append(_cyclic_part(exterior, start+gap, span))
    paths = inner_paths + exterior_paths
    for path in paths:
        if not path.is_simple or path.length <= 0:
            raise ValueError("Invalid compensated path")
        if path.distance(board) < radius:
            raise ValueError("Nominal cutter intersects retained board")
        if not stock_shape.covers(path) or path.distance(stock_shape.boundary) < radius:
            raise ValueError("Nominal cutter leaves stock")
    all_cuts = unary_union(paths)
    for _, _, width, center in intervals:
        if center.distance(all_cuts) < radius + width/2 - 1e-8:
            raise ValueError("Another cut interferes with tab")
    return CutoutPreview(tuple(map(_xy, inner_paths)), tuple(map(_xy, exterior_paths)),
                         tuple(map(_xy, gap_paths)), diameter_mm, offset, length)


def _panel_cutout(panel, stock, diameter, tabs, margin, clockwise):
    """Independent contours, common stock; conservative inter-board clearance."""
    material = geometry_from_outline(panel)
    shapes = [geometry_from_outline(b) for b in panel.boards]
    owned = [[] for _ in shapes]
    for tab in tabs:
        if not isinstance(tab, Tab):
            raise ValueError("Expected Tab")
        matches = [i for i,b in enumerate(shapes) if b.exterior.distance(Point(tab.anchor)) <= 1e-8]
        if len(matches)!=1:
            raise ValueError("Tab anchor must belong to exactly one board")
        owned[matches[0]].append(tab)
    plans = [plan_cutout_preview(b,stock,diameter,tabs=ts,margin_mm=margin,clockwise=clockwise)
             for b,ts in zip(panel.boards,owned)]
    cuts = [unary_union([LineString(p) for p in (*r.internal_paths,*r.exterior_paths)])
            for r in plans]
    radius = diameter/2
    for i,cut in enumerate(cuts):
        if cut.distance(material) < radius:
            raise ValueError("Panel cut intersects retained board material")
        for previous in cuts[:i]:
            if cut.distance(previous) < diameter:
                raise ValueError("Insufficient inter-board cutter clearance")
    all_cuts = unary_union(cuts)
    for plan,ts in zip(plans,owned):
        for gap,tab in zip(plan.tab_gaps,ts):
            center=LineString(gap).interpolate(0.5,normalized=True)
            if center.distance(all_cuts)<radius+tab.width_mm/2-1e-8:
                raise ValueError("Panel cut interferes with holding tab")
    return CutoutPreview(tuple(p for r in plans for p in r.internal_paths),
                         tuple(p for r in plans for p in r.exterior_paths),
                         tuple(p for r in plans for p in r.tab_gaps),
                         diameter, radius+margin,sum(r.exterior_full_length_mm for r in plans))
