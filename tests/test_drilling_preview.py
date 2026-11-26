"""Independent checks of read-only drill grouping, routing and board clearance."""
from collections import Counter
from pathlib import Path
from random import Random
import pytest

pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.domain.pcb import BoardOutline, Drill, DrillLayer, Slot
from pcb_studio.infrastructure.cam.drilling_preview import plan_drilling_preview

OUTER = ((0,0),(30,0),(30,20),(0,20),(0,0))
BOARD = BoardOutline("outline", OUTER)


def test_grouping_preserves_source_plating_and_operation():
    a = DrillLayer("PTH", (Drill((5,5),0.8,True), Drill((10,5),1.2,True)))
    b = DrillLayer("NPTH", (Drill((15,5),0.8,False),), (Slot((5,10),(10,10),0.8,False),))
    plan = plan_drilling_preview([a,b], BOARD)
    assert [(s.operation,s.diameter_mm) for s in plan.stages] == [
        ("drill",0.8),("drill",1.2),("mill_slot",0.8)]
    assert {(r.source,r.feature.plated) for r in plan.stages[0].features} == {
        ("PTH",True),("NPTH",False)}
    assert plan.stages[2].cutting_xy_mm == 5
    assert not plan.manufacturing_ready


def test_exact_sizes_not_rounded_together():
    layer = DrillLayer("d", (Drill((5,5),0.8), Drill((10,5),0.8001)))
    assert len(plan_drilling_preview([layer], BOARD).stages) == 2


def test_duplicate_report_preserves_multiplicity_and_conflicting_plating():
    a = DrillLayer("a",(Drill((5,5),0.8,True),))
    b = DrillLayer("b",(Drill((5,5),0.8,False),))
    plan = plan_drilling_preview([a,b], BOARD)
    assert len(plan.stages[0].features) == 2
    [(first,second)] = plan.duplicate_features
    assert (first.source,second.source) == ("a","b")
    assert first.feature.plated is True and second.feature.plated is False


def test_reverse_slot_duplicate_report_and_source_direction():
    a = Slot((5,5),(10,5),1)
    b = Slot((10,5),(5,5),1)
    plan = plan_drilling_preview([DrillLayer("s",slots=(a,b))], BOARD)
    assert tuple(r.feature for r in plan.stages[0].features) == (a,b)
    assert len(plan.duplicate_features) == 1
    assert plan.stages[0].cutting_xy_mm == 10


def test_optimization_preserves_features_and_improves_grid():
    points = [(2+3*x,2+3*y) for x in range(9) for y in range(6)]
    Random(17).shuffle(points)
    drills = tuple(Drill(p,0.8) for p in points)
    layer = DrillLayer("grid",drills)
    [stage] = plan_drilling_preview([layer],BOARD).stages
    assert Counter(r.feature for r in stage.features) == Counter(drills)
    assert stage.planned_rapid_mm < stage.input_rapid_mm
    assert stage.features == plan_drilling_preview([layer],BOARD).stages[0].features
    print(f"drill grid: {len(drills)} holes; {stage.input_rapid_mm:.9f} -> {stage.planned_rapid_mm:.9f} mm")


def test_no_optimization_keeps_order():
    drills = (Drill((20,10),1),Drill((5,5),1))
    [stage] = plan_drilling_preview([DrillLayer("d",drills)],BOARD,optimize=False).stages
    assert tuple(r.feature for r in stage.features) == drills
    assert stage.planned_rapid_mm == stage.input_rapid_mm


@pytest.mark.parametrize("feature", [
    Drill((0.4,5),1), Drill((31,5),1),
    Slot((0.4,5),(5,5),1), Slot((5,5),(31,5),1),
])
def test_rejects_edge_overrun(feature):
    layer = DrillLayer("d", (feature,) if isinstance(feature,Drill) else (),
                       (feature,) if isinstance(feature,Slot) else ())
    with pytest.raises(ValueError,match="outside board clearance"):
        plan_drilling_preview([layer],BOARD)


@pytest.mark.parametrize("feature", [Drill((10,10),1), Drill((7.7,10),1),
                                      Slot((5,10),(15,10),1)])
def test_cutout_rejected_even_when_slot_endpoints_inside(feature):
    outline = BoardOutline("cutout",OUTER,(((8,8),(12,8),(12,12),(8,12),(8,8)),))
    layer = DrillLayer("d", (feature,) if isinstance(feature,Drill) else (),
                       (feature,) if isinstance(feature,Slot) else ())
    with pytest.raises(ValueError,match="outside board clearance"):
        plan_drilling_preview([layer],outline)


def test_empty_layers_and_invalid_settings():
    assert not plan_drilling_preview([],BOARD).stages
    with pytest.raises(ValueError):
        plan_drilling_preview([],BOARD,edge_clearance_mm=-1)


def test_imported_synthetic_board():
    pytest.importorskip("gerbonara")
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    root = Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    importer = GerbonaraImporter()
    plan = plan_drilling_preview([importer.drills(root/"drills.drl")],
                                 importer.outline(root/"outline.gbr"))
    [stage] = plan.stages
    assert stage.diameter_mm == pytest.approx(1)
    assert {r.feature.center for r in stage.features} == {(5,10),(25,10)}
    assert not plan.duplicate_features
