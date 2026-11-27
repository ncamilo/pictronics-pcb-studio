"""Tab placement in canonical board coordinates; no changes to source geometry."""
from math import isfinite
from shapely.geometry import LineString, Point
from pcb_studio.domain.pcb import validate_xy
from pcb_studio.infrastructure.cam.cutout_preview import Tab, plan_cutout_preview
from pcb_studio.infrastructure.cam.geometry_job import assumed_stock


def snap_exterior(outline, xy, tolerance_mm):
    validate_xy(xy)
    if not isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError("Positive snap tolerance required")
    line=LineString(outline.exterior)
    point=Point(xy)
    if line.distance(point)>tolerance_mm:
        raise ValueError("Click closer to the exterior outline")
    projected=line.interpolate(line.project(point))
    return float(projected.x),float(projected.y)


def preset_anchors(outline, mode):
    """Nominal bbox side midpoints projected onto exterior; validate before use."""
    line=LineString(outline.exterior)
    xmin,ymin,xmax,ymax=line.bounds
    cx,cy=(xmin+xmax)/2,(ymin+ymax)/2
    lr=((xmin,cy),(xmax,cy))
    tb=((cx,ymin),(cx,ymax))
    if mode not in ("lr","tb","four"):
        raise ValueError("Unknown tab preset")
    seeds={"lr":lr,"tb":tb,"four":lr+tb}[mode]
    result=[]
    for xy in seeds:
        p=line.interpolate(line.project(Point(xy)))
        result.append((float(p.x),float(p.y)))
    return tuple(result)


def preview_tabs(outline, anchors, width, cutter, stock_margin):
    return plan_cutout_preview(outline,assumed_stock(outline,stock_margin),cutter,
                               tabs=tuple(Tab(tuple(xy),width) for xy in anchors))
