"""Tab placement in canonical board coordinates; no changes to source geometry."""
from math import isfinite
from shapely.geometry import LineString, Point
from pcb_studio.domain.pcb import validate_xy, outline_boards
from pcb_studio.infrastructure.cam.cutout_preview import Tab, plan_cutout_preview
from pcb_studio.infrastructure.cam.geometry_job import assumed_stock


def snap_exterior(outline, xy, tolerance_mm):
    validate_xy(xy)
    if not isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError("Positive snap tolerance required")
    point=Point(xy)
    lines=[LineString(b.exterior) for b in outline_boards(outline)]
    ranked=sorted((line.distance(point),i) for i,line in enumerate(lines))
    if len(ranked)>1 and abs(ranked[0][0]-ranked[1][0])<=1e-8:
        raise ValueError("Ambiguous board edge; zoom in")
    line=lines[ranked[0][1]]
    if line.distance(point)>tolerance_mm:
        raise ValueError("Click closer to the exterior outline")
    projected=line.interpolate(line.project(point))
    return float(projected.x),float(projected.y)


def preset_anchors(outline, mode):
    """Nominal bbox side midpoints projected onto exterior; validate before use."""
    boards=outline_boards(outline)
    if len(boards)>1:
        return tuple(xy for board in boards for xy in preset_anchors(board,mode))
    line=LineString(boards[0].exterior)
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
