"""Exercise offline traces with actual CAM geometry, not a machine."""
from dataclasses import replace
from math import dist
from pathlib import Path
import pytest
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.domain.pcb import BoardOutline,PCBProject,CopperLayer,CopperPolygon,DrillLayer,Drill,Slot
from pcb_studio.domain.tools import CuttingTool,ToolLibrary,ProcessSettings
from pcb_studio.domain.depth import DepthSetup
from pcb_studio.infrastructure.cam.job_preview import plan_job_preview
from pcb_studio.infrastructure.cam.cutout_preview import Tab
from pcb_studio.infrastructure.cam.tool_binding import ToolSelection,bind_job_tools,isolation_tool_spec
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview


def rect(x,y,w,h):
    return ((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y))


LIB=ToolLibrary((CuttingTool("v","V","v_bit",3.175,1,0.1,30),
                 CuttingTool("d","D","drill",1,3),
                 CuttingTool("e","E","end_mill",1,3)))
ISO=ToolSelection("v",ProcessSettings(0.1,0.1,30,10000,100))
DRILL=ToolSelection("d",ProcessSettings(1.6,0.8,30,10000))
CUT=ToolSelection("e",ProcessSettings(1.6,0.8,30,10000,80))
SETUP=DepthSetup(1.6,3,0.1)
STOCK=BoardOutline("stock",rect(-5,-5,40,30))
TABS=tuple(Tab(p,2) for p in ((15,0),(30,10),(15,20),(0,10)))


def bound_job(complex_board=False):
    holes=(rect(12,8,6,4),) if complex_board else ()
    board=BoardOutline("board",rect(0,0,30,20),holes)
    copper=CopperLayer("bottom","bottom",(CopperPolygon(rect(5,5,4,4)),))
    slots=(Slot((20,5),(24,5),1),) if complex_board else ()
    project=PCBProject("fixture",(copper,),(DrillLayer("d",(Drill((7,7),1),),slots),),board)
    preview=plan_job_preview(project,STOCK,isolation_tools=(isolation_tool_spec(LIB,ISO),),
                             target_width_mm=0.15,cutout_diameter_mm=1,tabs=TABS)
    selections=(ISO,DRILL,CUT,CUT,CUT) if complex_board else (ISO,DRILL,CUT)
    return bind_job_tools(preview,LIB,selections)


def assert_invariants(trace):
    current=trace.initial_position
    for e in trace.events:
        assert e.start==current
        if e.kind in ("rapid_xy","tool_setup"):
            assert e.start[2]==e.end[2]==trace.setup.safe_z_mm
            assert e.feed_mm_min is None
        if e.kind in ("plunge","retract"):
            assert e.start[:2]==e.end[:2]
            if e.kind=="plunge":
                assert e.start[2]==trace.setup.safe_z_mm and e.end[2]<0
                assert e.feed_mm_min>0
            else:
                assert e.end[2]==trace.setup.safe_z_mm
        if e.kind=="cut_xy":
            assert e.start[2]==e.end[2]<0 and e.feed_mm_min>0
        current=e.end
    assert current[2]==trace.setup.safe_z_mm
    assert not trace.manufacturing_ready


def test_full_trace_and_depths():
    b=bound_job()
    t=plan_motion_preview(b,SETUP,start_xy=(0,0))
    assert_invariants(t)
    assert [e.tool_id for e in t.events if e.kind=="tool_setup"]==["v","d","e"]
    for i,depths in enumerate(({-0.1},{-0.8,-1.6},{-0.8,-1.6})):
        assert {e.end[2] for e in t.events if e.stage_index==i and e.kind=="plunge"}==depths
    assert not any(e.kind=="cut_xy" and e.stage_index==1 for e in t.events)
    assert t.cutting_xy_mm==pytest.approx(b.job.stages[0].cutting_xy_mm+
                                          2*b.job.stages[-1].cutting_xy_mm)
    assert len([e for e in t.events if e.kind=="plunge" and e.stage_index==2])==8
    print(f"XYZ trace: events={len(t.events)}, cutting_xy={t.cutting_xy_mm:.9f}, "
          f"rapid_xy={t.rapid_xy_mm:.9f}, vertical={t.vertical_mm:.9f}")


def test_slot_and_internal_before_exterior():
    b=bound_job(True)
    t=plan_motion_preview(b,SETUP,start_xy=(0,0))
    assert_invariants(t)
    assert [s.stage.operation for s in b.stages]==[
        "isolation","drill","mill_slot","cutout_internal","cutout_external"]
    assert [e.stage_index for e in t.events if e.kind=="tool_setup"]==list(range(5))
    cuts=[e for e in t.events if e.kind=="cut_xy" and e.stage_index==2]
    assert len(cuts)==2
    assert sum(dist(e.start,e.end) for e in cuts)==8
    assert t.bound.job.diagnostics==b.job.diagnostics


def test_tab_segments_not_connected_at_depth():
    b=bound_job()
    t=plan_motion_preview(b,SETUP,start_xy=(0,0))
    expected={(tuple(a),tuple(c)) for path in b.job.cutout.exterior_paths
              for a,c in zip(path,path[1:]) if a!=c}
    cuts=[e for e in t.events if e.kind=="cut_xy" and e.stage_index==2]
    assert {(e.start[:2],e.end[:2]) for e in cuts}==expected
    assert len(cuts)==2*len(expected)


def test_reject_inconsistent_stock_and_stage():
    b=bound_job()
    with pytest.raises(ValueError,match="Through-cut"):
        plan_motion_preview(b,DepthSetup(1.7,3,0.1),start_xy=(0,0))
    with pytest.raises(ValueError,match="Through-cut"):
        plan_motion_preview(b,DepthSetup(1.4,3,0.1),start_xy=(0,0))
    with pytest.raises(ValueError,match="stages"):
        plan_motion_preview(replace(b,stages=b.stages[:-1]),SETUP,start_xy=(0,0))


def test_actual_import_trace():
    pytest.importorskip("gerbonara")
    from pcb_studio.application.import_project import import_project
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    p=import_project(GerbonaraImporter(),"synthetic",
                     copper_files=((root/"bottom.gbr","bottom"),),
                     drill_files=(root/"drills.drl",),outline_file=root/"outline.gbr")
    j=plan_job_preview(p,STOCK,isolation_tools=(isolation_tool_spec(LIB,ISO),),
                       target_width_mm=0.15,cutout_diameter_mm=1,tabs=TABS)
    t=plan_motion_preview(bind_job_tools(j,LIB,(ISO,DRILL,CUT)),SETUP,start_xy=(0,0))
    assert_invariants(t)
    assert len([e for e in t.events if e.kind=="plunge" and e.stage_index==1])==4
    print(f"imported XYZ trace: events={len(t.events)}, cutting_xy={t.cutting_xy_mm:.9f}, "
          f"rapid_xy={t.rapid_xy_mm:.9f}, vertical={t.vertical_mm:.9f}")
