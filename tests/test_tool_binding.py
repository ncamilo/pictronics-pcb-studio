"""Bind actual imported preview geometry to explicit experimental settings."""
from pathlib import Path
from dataclasses import replace
import pytest
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.domain.pcb import PCBProject, CopperLayer, CopperPolygon, BoardOutline, DrillLayer, Drill
from pcb_studio.domain.tools import CuttingTool, ToolLibrary, ProcessSettings
from pcb_studio.infrastructure.cam.job_preview import plan_job_preview
from pcb_studio.infrastructure.cam.cutout_preview import Tab
from pcb_studio.infrastructure.cam.tool_binding import (
    ToolSelection, bind_job_tools, isolation_tool_spec,
)

LIB=ToolLibrary((CuttingTool("v","V","v_bit",3.175,1,0.1,30),
                 CuttingTool("d","D","drill",1,3),
                 CuttingTool("e","E","end_mill",1,3)))
ISO=ToolSelection("v",ProcessSettings(0.1,0.1,30,10000,100))
DRILL=ToolSelection("d",ProcessSettings(1.6,0.8,30,10000))
CUT=ToolSelection("e",ProcessSettings(1.6,0.8,30,10000,80))


def rect(x,y,w,h):
    return ((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y))


def job():
    board=BoardOutline("board",rect(0,0,30,20))
    stock=BoardOutline("stock",rect(-5,-5,40,30))
    copper=CopperLayer("bottom","bottom",(CopperPolygon(rect(5,5,10,5)),))
    project=PCBProject("fixture",(copper,),(DrillLayer("d",(Drill((7,7),1),)),),board)
    return plan_job_preview(project,stock,isolation_tools=(isolation_tool_spec(LIB,ISO),),
                            target_width_mm=0.15,cutout_diameter_mm=1,
                            tabs=tuple(Tab(p,2) for p in ((15,0),(30,10),(15,20),(0,10))))


def test_full_binding_preserves_geometry_and_diagnostics():
    p=job()
    b=bind_job_tools(p,LIB,(ISO,DRILL,CUT))
    assert b.job is p
    assert [s.tool.tool_id for s in b.stages]==["v","d","e"]
    assert b.stages[0].effective_diameter_mm==pytest.approx(0.15358983848622455)
    assert not b.manufacturing_ready
    assert b.job.diagnostics==p.diagnostics
    print(f"bound preview: V effective diameter={b.stages[0].effective_diameter_mm:.9f} mm; "
          f"stages={len(b.stages)}; nominal cutting XY={p.cutting_xy_mm:.9f} mm")


def test_equal_diameter_cannot_swap_drill_and_mill():
    with pytest.raises(ValueError,match="incompatible"):
        bind_job_tools(job(),LIB,(ISO,replace(DRILL,tool_id="e"),CUT))
    with pytest.raises(ValueError,match="incompatible"):
        bind_job_tools(job(),LIB,(ISO,DRILL,replace(CUT,tool_id="d")))


def test_changed_v_depth_requires_regeneration():
    changed=replace(ISO,settings=replace(ISO.settings,depth_mm=0.2,max_stepdown_mm=0.2))
    with pytest.raises(ValueError,match="regenerate"):
        bind_job_tools(job(),LIB,(changed,DRILL,CUT))


def test_missing_or_unknown_selection():
    with pytest.raises(ValueError,match="One tool"):
        bind_job_tools(job(),LIB,(ISO,DRILL))
    with pytest.raises(ValueError,match="Unknown"):
        bind_job_tools(job(),LIB,(ISO,DRILL,replace(CUT,tool_id="unknown")))


def test_imported_project_binding():
    pytest.importorskip("gerbonara")
    from pcb_studio.application.import_project import import_project
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    p=import_project(GerbonaraImporter(),"synthetic",
                     copper_files=((root/"bottom.gbr","bottom"),),
                     drill_files=(root/"drills.drl",),outline_file=root/"outline.gbr")
    preview=plan_job_preview(p,BoardOutline("stock",rect(-5,-5,40,30)),
                             isolation_tools=(isolation_tool_spec(LIB,ISO),),
                             target_width_mm=0.15,cutout_diameter_mm=1,
                             tabs=tuple(Tab(q,2) for q in ((15,0),(30,10),(15,20),(0,10))))
    bound=bind_job_tools(preview,LIB,(ISO,DRILL,CUT))
    assert [s.stage.operation for s in bound.stages]==["isolation","drill","cutout_external"]
    assert bound.stages[1].stage.feature_count==2
