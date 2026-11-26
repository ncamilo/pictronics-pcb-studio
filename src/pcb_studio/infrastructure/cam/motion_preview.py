"""Offline nominal XYZ trace. Not a G-code generator or machine command API."""
from dataclasses import dataclass
from math import dist, isclose, isfinite
from typing import Literal

from pcb_studio.domain.depth import DepthSetup, depth_levels, validate_depth
from pcb_studio.domain.pcb import Drill, Slot, validate_xy
from pcb_studio.domain.tools import validate_operation
from pcb_studio.infrastructure.cam.tool_binding import BoundJobPreview

XYZ = tuple[float,float,float]
EventKind = Literal["tool_setup","rapid_xy","plunge","cut_xy","retract"]


@dataclass(frozen=True)
class PreviewEvent:
    kind: EventKind
    stage_index: int
    tool_id: str
    start: XYZ
    end: XYZ
    feed_mm_min: float | None = None


@dataclass(frozen=True)
class MotionPreview:
    bound: BoundJobPreview
    setup: DepthSetup
    initial_position: XYZ
    events: tuple[PreviewEvent,...]

    @property
    def cutting_xy_mm(self):
        return sum(dist(e.start,e.end) for e in self.events if e.kind=="cut_xy")

    @property
    def rapid_xy_mm(self):
        return sum(dist(e.start,e.end) for e in self.events if e.kind=="rapid_xy")

    @property
    def vertical_mm(self):
        return sum(abs(e.end[2]-e.start[2]) for e in self.events
                   if e.kind in ("plunge","retract"))

    @property
    def manufacturing_ready(self):
        return False


def _paths(bound_stage, job):
    s=bound_stage.stage
    if s.operation=="isolation":
        return tuple(r.coordinates for r in job.isolation.stages[s.source_index].rings)
    if s.operation in ("drill","mill_slot"):
        refs=job.drilling.stages[s.source_index].features
        if s.operation=="drill":
            if any(not isinstance(r.feature,Drill) for r in refs):
                raise ValueError("Invalid drill reference")
            return tuple((r.feature.center,) for r in refs)
        if any(not isinstance(r.feature,Slot) for r in refs):
            raise ValueError("Invalid slot reference")
        return tuple((r.feature.start,r.feature.end) for r in refs)
    if s.operation=="cutout_internal":
        return job.cutout.internal_paths
    if s.operation=="cutout_external":
        return job.cutout.exterior_paths
    raise ValueError("Unknown preview operation")


def plan_motion_preview(bound: BoundJobPreview, setup: DepthSetup, *, start_xy):
    """Expand geometry into an immutable trace with explicit full retracts.

    Initial tool-tip position is assumed at safe Z in board coordinates.
    tool_setup is a simulation marker, not a tool change command; a separate
    marker per stage prevents implied reuse of an earlier setup. Every
    depth level and path has its own retract, including drill levels and
    separate tab segments. No plunge capability, fixture, spindle, machine
    bounds, workholding, tool length or real surface verification is implied.
    """
    if not isinstance(bound,BoundJobPreview) or not isinstance(setup,DepthSetup):
        raise ValueError("Expected bound job and depth setup")
    validate_xy(start_xy)
    if tuple(b.stage for b in bound.stages)!=bound.job.stages:
        raise ValueError("Bound stages differ from job")
    prepared=[]
    budget=0
    for b in bound.stages:
        s=b.stage
        settings=b.settings
        diameter=validate_operation(b.tool,s.operation,settings)
        if not isclose(diameter,s.diameter_mm,rel_tol=0,abs_tol=1e-9):
            raise ValueError("Tool geometry changed")
        validate_depth(s.operation,settings.depth_mm,setup)
        levels=depth_levels(settings.depth_mm,settings.max_stepdown_mm)
        paths=_paths(b,bound.job)
        if len(paths)!=s.feature_count or not paths:
            raise ValueError("Stage feature count mismatch")
        for path in paths:
            if not path or (s.operation!="drill" and len(path)<2):
                raise ValueError("Invalid preview path")
            for xy in path:
                validate_xy(xy)
        budget+=1+len(levels)*sum(len(path)+2 for path in paths)
        if budget>1_000_000:
            raise ValueError("Motion preview exceeds event budget")
        prepared.append((b,levels,paths))
    initial=(*start_xy,setup.safe_z_mm)
    current=initial
    events=[]
    for i,(b,levels,paths) in enumerate(prepared):
        tool_id=b.tool.tool_id
        settings=b.settings

        def add(kind,end,feed=None):
            nonlocal current
            end=tuple(end)
            if not all(isfinite(v) for v in end):
                raise ValueError("Nonfinite motion target")
            events.append(PreviewEvent(kind,i,tool_id,current,end,feed))
            current=end

        add("tool_setup",current)
        for path in paths:
            for z in levels:
                entry=(*path[0],setup.safe_z_mm)
                if current!=entry:
                    add("rapid_xy",entry)
                add("plunge",(*path[0],z),settings.plunge_mm_min)
                for xy in path[1:]:
                    if current!=(*xy,z):
                        add("cut_xy",(*xy,z),settings.feed_xy_mm_min)
                add("retract",(*current[:2],setup.safe_z_mm))
    return MotionPreview(bound,setup,initial,tuple(events))
