"""Independent offline trace conformance check against the bound CAM job.

Does not call the motion generator. This is not physical collision validation
or machine authorization. Source geometry and process settings remain nominal.
"""
from dataclasses import dataclass
from math import ceil, dist, isclose, isfinite

from pcb_studio.domain.pcb import Drill, Slot
from pcb_studio.domain.tools import validate_operation
from pcb_studio.infrastructure.cam.motion_preview import MotionPreview, PreviewEvent


class MotionValidationError(ValueError):
    """First detected inconsistency in an offline trace."""


@dataclass(frozen=True)
class MotionValidation:
    event_count: int
    stage_count: int
    path_cycles: int
    cutting_xy_mm: float
    rapid_xy_mm: float
    vertical_mm: float
    bounds_xyz: tuple[tuple[float,float,float], tuple[float,float,float]]
    diagnostic_codes: tuple[str,...]

    @property
    def manufacturing_ready(self):
        return False


def _require(condition, message):
    if not condition:
        raise MotionValidationError(message)


def _xyz(point):
    return (isinstance(point,tuple) and len(point)==3
            and all(type(v) in (int,float) and isfinite(v) for v in point))


def _source_paths(stage, job):
    """Read original source records, without using the generator's path helper."""
    op, idx = stage.operation, stage.source_index
    if op == "isolation":
        _require(type(idx) is int and 0 <= idx < len(job.isolation.stages),
                 "Invalid isolation source index")
        source = job.isolation.stages[idx]
        _require(source.rejection is None and source.tool.diameter_mm == stage.diameter_mm,
                 "Invalid isolation source")
        return tuple(r.coordinates for r in source.rings)
    if op in ("drill","mill_slot"):
        _require(type(idx) is int and 0 <= idx < len(job.drilling.stages),
                 "Invalid drill source index")
        source = job.drilling.stages[idx]
        _require(source.operation == op and source.diameter_mm == stage.diameter_mm,
                 "Drill source metadata mismatch")
        paths = []
        for ref in source.features:
            feature = ref.feature
            _require(feature.diameter_mm == stage.diameter_mm,"Feature diameter mismatch")
            if op == "drill":
                _require(isinstance(feature,Drill),"Expected drill feature")
                paths.append((feature.center,))
            else:
                _require(isinstance(feature,Slot),"Expected slot feature")
                paths.append((feature.start,feature.end))
        return tuple(paths)
    _require(op in ("cutout_internal","cutout_external") and idx is None
             and stage.diameter_mm == job.cutout.diameter_mm,"Invalid cutout source")
    return job.cutout.internal_paths if op == "cutout_internal" else job.cutout.exterior_paths


def validate_motion_preview(trace: MotionPreview):
    """Check exact path vertices, direction, depth order, feeds and continuity.

    Strict canonical trace format; equivalent reordered or subdivided moves
    are deliberately not accepted. Coordinate matching is exact for XY;
    depth matching allows 1e-12 mm numerical roundoff only. Fails at first
    inconsistency. Reports observed tip-coordinate bounds, not machine limits.
    """
    _require(isinstance(trace,MotionPreview),"Expected MotionPreview")
    job, setup = trace.bound.job, trace.setup
    safe = setup.safe_z_mm
    _require(isfinite(safe) and safe > 0 and isfinite(setup.thickness_mm)
             and setup.thickness_mm > 0 and isfinite(setup.breakthrough_limit_mm)
             and setup.breakthrough_limit_mm >= 0,"Invalid setup")
    _require(_xyz(trace.initial_position) and trace.initial_position[2] == safe,
             "Invalid initial position")
    _require(tuple(b.stage for b in trace.bound.stages)==job.stages and bool(job.stages),
             "Bound stage mismatch")
    _require(type(trace.events) is tuple and len(trace.events)<=1_000_000,
             "Invalid event container or budget")
    phases = {"isolation":0,"drill":1,"mill_slot":2,"cutout_internal":3,"cutout_external":4}
    ranks = [phases.get(s.operation,-1) for s in job.stages]
    _require(-1 not in ranks and ranks==sorted(ranks) and ranks[-1]==4
             and ranks.count(4)==1,"Invalid CAM stage order")

    pos = trace.initial_position
    mins, maxs = list(pos),list(pos)
    cursor = cycles = 0
    cut = rapid = vertical = 0.0

    def consume(kind,stage_index,tool_id,end,feed=None):
        nonlocal cursor,pos,cut,rapid,vertical
        _require(cursor<len(trace.events),f"Missing {kind} at event {cursor}")
        event = trace.events[cursor]
        prefix = f"Event {cursor}: "
        _require(isinstance(event,PreviewEvent),prefix+"Invalid event type")
        _require(_xyz(event.start) and _xyz(event.end),prefix+"Nonfinite or malformed XYZ")
        _require(event.start==pos,prefix+"Discontinuous start")
        _require(event.kind==kind and event.stage_index==stage_index
                 and event.tool_id==tool_id,prefix+"Unexpected event, stage or tool")
        _require(event.end[:2]==end[:2] and
                 isclose(event.end[2],end[2],rel_tol=0,abs_tol=1e-12),
                 prefix+"Unexpected coordinate or depth")
        if kind in ("rapid_xy","tool_setup","retract"):
            _require(event.end[2]==safe,prefix+"Safe Z mismatch")
        if kind=="tool_setup":
            _require(event.start==event.end,prefix+"Setup must not move")
        if kind=="rapid_xy":
            _require(event.start[2]==safe,prefix+"Rapid below safe Z")
        if kind in ("plunge","retract"):
            _require(event.start[:2]==event.end[:2],prefix+"Nonvertical move")
        if kind=="plunge":
            _require(event.start[2]==safe and event.end[2]<0,prefix+"Invalid plunge")
        if kind=="retract":
            _require(event.start[2]<0,prefix+"Invalid retract")
        if kind=="cut_xy":
            _require(event.start[2]==event.end[2]<0,prefix+"Nonplanar cut")
        if feed is None:
            _require(event.feed_mm_min is None,prefix+"Unexpected feed")
        else:
            _require(type(event.feed_mm_min) in (float,int)
                     and isfinite(event.feed_mm_min) and event.feed_mm_min>0
                     and event.feed_mm_min==feed,prefix+"Feed mismatch")
        delta=dist(event.start,event.end)
        _require(isfinite(delta),prefix+"Nonfinite travel")
        if kind=="cut_xy":
            cut+=delta
        elif kind=="rapid_xy":
            rapid+=delta
        elif kind in ("plunge","retract"):
            vertical+=delta
        pos=event.end
        for axis,value in enumerate(pos):
            mins[axis]=min(mins[axis],value)
            maxs[axis]=max(maxs[axis],value)
        cursor+=1

    for i,b in enumerate(trace.bound.stages):
        s,settings,tool=b.stage,b.settings,b.tool
        try:
            dia=validate_operation(tool,s.operation,settings)
        except ValueError as exc:
            raise MotionValidationError(str(exc)) from exc
        _require(isclose(dia,s.diameter_mm,rel_tol=0,abs_tol=1e-9)
                 and isclose(dia,b.effective_diameter_mm,rel_tol=0,abs_tol=1e-9),
                 "Tool diameter mismatch")
        depth,step=settings.depth_mm,settings.max_stepdown_mm
        if s.operation=="isolation":
            _require(depth<setup.thickness_mm,"Isolation reaches board underside")
        else:
            _require(setup.thickness_mm<=depth<=setup.thickness_mm+setup.breakthrough_limit_mm,
                     "Through depth outside setup interval")
        ratio=depth/step
        _require(isfinite(ratio) and 1<=ratio<=10000,"Invalid depth schedule")
        n=ceil(ratio)
        paths=_source_paths(s,job)
        _require(len(paths)==s.feature_count and bool(paths),"Feature count mismatch")
        consume("tool_setup",i,tool.tool_id,pos)
        for path in paths:
            _require(len(path)==1 if s.operation=="drill" else len(path)>=2,
                     "Invalid source path")
            for level in range(1,n+1):
                z=-depth if level==n else -depth*(level/n)
                entry=(*path[0],safe)
                if pos!=entry:
                    consume("rapid_xy",i,tool.tool_id,entry)
                consume("plunge",i,tool.tool_id,(*path[0],z),settings.plunge_mm_min)
                for xy in path[1:]:
                    if pos[:2]!=xy:
                        consume("cut_xy",i,tool.tool_id,(*xy,z),settings.feed_xy_mm_min)
                consume("retract",i,tool.tool_id,(*pos[:2],safe))
                cycles+=1
    _require(cursor==len(trace.events),"Unexpected trailing events")
    _require(pos[2]==safe and all(isfinite(v) for v in (cut,rapid,vertical)),
             "Invalid final trace")
    return MotionValidation(cursor,len(job.stages),cycles,cut,rapid,vertical,
                            (tuple(mins),tuple(maxs)),
                            tuple(d.code for d in job.diagnostics))
