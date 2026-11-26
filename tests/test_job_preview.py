"""Cross-engine integration checks; no executable machine operations."""
from dataclasses import replace
from pathlib import Path

import pytest
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.domain.pcb import (
    PCBProject, CopperLayer, CopperPolygon, BoardOutline, DrillLayer, Drill, Slot,
)
from pcb_studio.infrastructure.cam.job_preview import plan_job_preview
from pcb_studio.infrastructure.cam.multi_tool_preview import ToolSpec
from pcb_studio.infrastructure.cam.cutout_preview import Tab


def rect(x,y,w,h):
    return ((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y))


OUTLINE = BoardOutline("edges", rect(0,0,30,20), (rect(12,8,6,4),))
STOCK = BoardOutline("stock",rect(-5,-5,40,30))
COPPER = CopperLayer("top.gbr","top",(CopperPolygon(rect(4,4,4,4)),))
DRILLS = DrillLayer("drills",(Drill((5,5),0.8,True),Drill((10,5),1.2,False)),
                    (Slot((20,5),(24,5),0.8,False),))
PROJECT = PCBProject("fixture",(COPPER,),(DRILLS,),OUTLINE)
TABS = tuple(Tab(p,2) for p in ((15,0),(30,10),(15,20),(0,10)))


def plan(project=PROJECT, **kwargs):
    settings = dict(isolation_tools=(ToolSpec(0.4),),target_width_mm=0.4,
                    cutout_diameter_mm=1,tabs=TABS)
    settings.update(kwargs)
    return plan_job_preview(project,STOCK,**settings)


def test_integrated_stage_sequence_and_traceability():
    result = plan()
    assert [(s.operation,s.diameter_mm,s.feature_count) for s in result.stages] == [
        ("isolation",0.4,1),("drill",0.8,1),("drill",1.2,1),
        ("mill_slot",0.8,1),("cutout_internal",1,1),("cutout_external",1,4)]
    for s in result.stages:
        if s.operation == "isolation":
            assert s.cutting_xy_mm == result.isolation.stages[s.source_index].selected_length_mm
        elif s.operation in ("drill","mill_slot"):
            assert s.diameter_mm == result.drilling.stages[s.source_index].diameter_mm
    assert result.cutting_xy_mm == pytest.approx(
        result.isolation.stages[0].selected_length_mm + 4 + 15.984 + 91.154079856)
    assert not result.manufacturing_ready
    assert "internal_slug_retention_unverified" in {d.code for d in result.diagnostics}


def test_isolation_tool_order_and_redundant_stage_omission():
    result = plan(isolation_tools=(ToolSpec(0.4),ToolSpec(0.4)))
    assert len(result.isolation.stages)==2
    assert [s.source_index for s in result.stages if s.operation=="isolation"] == [0]


def test_duplicate_features_remain_visible():
    duplicate=DrillLayer("duplicate",(DRILLS.drills[0],))
    result=plan(replace(PROJECT,drills=(DRILLS,duplicate)))
    assert len(result.drilling.duplicate_features)==1
    assert "duplicate_drill_features" in {d.code for d in result.diagnostics}
    assert not result.manufacturing_ready


def test_uncovered_critical_gap_remains_visible():
    copper=CopperLayer("top","top",(CopperPolygon(rect(3,3,4,4)),
                                    CopperPolygon(rect(7.2,3,3.8,4))))
    result=plan(replace(PROJECT,copper=(copper,)),critical_points=((7.1,5),))
    assert result.isolation.uncovered_probe_indices==(0,)
    assert {"residual_isolation","uncovered_critical_points"} <= {d.code for d in result.diagnostics}


def test_rejected_isolation_and_empty_stage_diagnostic():
    copper=CopperLayer("top","top",(CopperPolygon(rect(0.1,3,4,4)),))
    result=plan(replace(PROJECT,copper=(copper,)))
    assert {"isolation_tool_rejected","no_isolation_paths","residual_isolation"} <= {
        d.code for d in result.diagnostics}
    assert not any(s.operation=="isolation" for s in result.stages)


def test_no_drills_or_tabs_are_explicit():
    result=plan(replace(PROJECT,drills=()),tabs=())
    assert {"no_drill_features","no_external_tabs"} <= {d.code for d in result.diagnostics}
    assert result.stages[-1].operation=="cutout_external"


def test_bottom_side_preserves_canonical_frame():
    result=plan(replace(PROJECT,copper=(replace(COPPER,side="bottom"),)))
    original=plan()
    assert result.copper_side=="bottom"
    assert result.isolation==original.isolation
    assert result.drilling==original.drilling


@pytest.mark.parametrize("project", [
    replace(PROJECT,outline=None),
    replace(PROJECT,copper=()),
    replace(PROJECT,copper=(COPPER,replace(COPPER,side="bottom"))),
    replace(PROJECT,drills=(DrillLayer("invalid",(Drill((0.1,5),1),)),)),
    replace(PROJECT,outline=BoardOutline("bad",rect(0,0,30,20),(rect(12,8,0.8,4),))),
])
def test_invalid_job_never_returns_partial_plan(project):
    with pytest.raises(ValueError):
        plan(project)


def test_stock_required_and_residual_threshold_validation():
    with pytest.raises(ValueError,match="stock"):
        plan_job_preview(PROJECT,None,isolation_tools=(ToolSpec(0.4),),
                         target_width_mm=0.4,cutout_diameter_mm=1)
    with pytest.raises(ValueError,match="threshold"):
        plan(residual_report_threshold_mm2=-1)


def test_actual_import_to_integrated_preview():
    pytest.importorskip("gerbonara")
    from pcb_studio.application.import_project import import_project
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    folder=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    project=import_project(GerbonaraImporter(),"synthetic-board",
                           copper_files=((folder/"bottom.gbr","bottom"),),
                           drill_files=(folder/"drills.drl",),
                           outline_file=folder/"outline.gbr")
    result=plan(project)
    assert [s.operation for s in result.stages]==["isolation","drill","cutout_external"]
    assert result.stages[1].feature_count==2
    assert result.stages[-1].feature_count==4
    assert result.copper_side=="bottom"
    assert not result.manufacturing_ready
    print(f"integrated synthetic board: stages={len(result.stages)}; "
          f"cutting_xy={result.cutting_xy_mm:.9f} mm; "
          f"residual={result.isolation.residual_mm2:.9f} mm2; "
          f"diagnostics={[d.code for d in result.diagnostics]}")
