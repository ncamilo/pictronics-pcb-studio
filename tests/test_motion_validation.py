"""Mutate known-good traces to test the independent conformance checker."""
from dataclasses import replace
import pytest
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
from pcb_studio.infrastructure.cam.motion_validation import (
    validate_motion_preview, MotionValidationError,
)
from test_motion_preview import bound_job, SETUP


@pytest.fixture
def trace():
    return plan_motion_preview(bound_job(True),SETUP,start_xy=(0,0))


def test_valid_trace_metrics(trace):
    report=validate_motion_preview(trace)
    assert report.event_count==len(trace.events)
    assert report.stage_count==5
    assert report.path_cycles==15
    assert report.cutting_xy_mm==pytest.approx(trace.cutting_xy_mm)
    assert report.rapid_xy_mm==pytest.approx(trace.rapid_xy_mm)
    assert report.vertical_mm==pytest.approx(trace.vertical_mm)
    assert report.bounds_xyz[0][2]==-1.6 and report.bounds_xyz[1][2]==3
    assert report.diagnostic_codes==tuple(d.code for d in trace.bound.job.diagnostics)
    assert not report.manufacturing_ready
    print(f"validated XYZ: events={report.event_count}; stages={report.stage_count}; "
          f"path_cycles={report.path_cycles}; bounds={report.bounds_xyz}")


def mutate(trace,kind,**changes):
    events=list(trace.events)
    i=next(i for i,e in enumerate(events) if e.kind==kind)
    events[i]=replace(events[i],**changes)
    return replace(trace,events=tuple(events))


@pytest.mark.parametrize("kind,changes",[
    ("rapid_xy",{"end":(0,0,-0.1)}),
    ("plunge",{"feed_mm_min":0}),
    ("plunge",{"end":(float("nan"),0,-0.1)}),
    ("plunge",{"tool_id":"wrong"}),
    ("cut_xy",{"stage_index":99}),
    ("cut_xy",{"feed_mm_min":999}),
    ("retract",{"end":(0,0,0)}),
    ("tool_setup",{"end":(1,1,3)}),
])
def test_mutations_rejected(trace,kind,changes):
    with pytest.raises(MotionValidationError):
        validate_motion_preview(mutate(trace,kind,**changes))


@pytest.mark.parametrize("mode",["delete","duplicate","reverse","truncate","append"])
def test_event_sequence_mutation(trace,mode):
    events=list(trace.events)
    i=next(i for i,e in enumerate(events) if e.kind=="cut_xy")
    if mode=="delete":
        del events[i]
    elif mode=="duplicate":
        events.insert(i,events[i])
    elif mode=="reverse":
        events[i],events[i+1]=events[i+1],events[i]
    elif mode=="truncate":
        events.pop()
    else:
        events.append(events[-1])
    with pytest.raises(MotionValidationError):
        validate_motion_preview(replace(trace,events=tuple(events)))


def test_continuous_but_wrong_vertex(trace):
    events=list(trace.events)
    i=next(i for i,e in enumerate(events) if e.kind=="cut_xy")
    x,y,z=events[i].end
    wrong=(x+0.01,y,z)
    events[i]=replace(events[i],end=wrong)
    events[i+1]=replace(events[i+1],start=wrong)
    with pytest.raises(MotionValidationError,match="coordinate"):
        validate_motion_preview(replace(trace,events=tuple(events)))


def test_continuous_tab_bridge_rejected(trace):
    events=list(trace.events)
    i=next(i for i,e in enumerate(events) if e.kind=="retract" and e.stage_index==4)
    e=events[i]
    # Forge a lateral cut across the intended retraction boundary.
    events[i]=replace(e,kind="cut_xy",end=(e.start[0]+3,e.start[1],e.start[2]),
                      feed_mm_min=80)
    events[i+1]=replace(events[i+1],start=events[i].end)
    with pytest.raises(MotionValidationError,match="Unexpected event"):
        validate_motion_preview(replace(trace,events=tuple(events)))


def test_wrong_bound_diameter(trace):
    stages=list(trace.bound.stages)
    stages[0]=replace(stages[0],effective_diameter_mm=0.4)
    with pytest.raises(MotionValidationError,match="diameter"):
        validate_motion_preview(replace(trace,bound=replace(trace.bound,stages=tuple(stages))))


def test_initial_and_final_height(trace):
    with pytest.raises(MotionValidationError,match="initial"):
        validate_motion_preview(replace(trace,initial_position=(0,0,0)))
    with pytest.raises(MotionValidationError):
        validate_motion_preview(replace(trace,events=trace.events[:-1]))


def test_single_side_original_fixture():
    t=plan_motion_preview(bound_job(),SETUP,start_xy=(0,0))
    report=validate_motion_preview(t)
    assert report.event_count==823
    assert report.path_cycles==11
