"""Independent geometric probes for the residual-aware whole-ring planner."""
import pytest
pytest.importorskip("shapely")
from shapely import from_wkb
from shapely.geometry import box, Point, LineString, LinearRing
from pcb_studio.infrastructure.cam.multi_tool_preview import (
    ToolSpec, plan_multi_tool_preview,
)

BOARD = box(0, 0, 20, 20)


def test_coarse_then_fine_reaches_gap():
    copper = box(3, 3, 7, 7).union(box(7.2, 3, 11, 7))
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.4), ToolSpec(0.15)],
                                  target_width_mm=0.4, critical_points=[(7.1, 5)])
    coarse, fine = plan.stages
    assert coarse.rings and fine.rings
    assert not coarse.rings[0].newly_covered_probes
    assert any(r.newly_covered_probes == (0,) for r in fine.rings)
    assert not plan.uncovered_probe_indices
    assert fine.residual_mm2 < coarse.residual_mm2
    assert not from_wkb(plan.residual_wkb_hex).covers(Point(7.1, 5))
    assert not plan.manufacturing_ready
    assert plan.covered_mm2 + plan.residual_mm2 == pytest.approx(plan.target_mm2)
    print(f"multi-tool gap: target={plan.target_mm2:.9f}; "
          f"coarse residual={coarse.residual_mm2:.9f}; "
          f"final residual={plan.residual_mm2:.9f}; coverage={plan.coverage_fraction:.9f}; "
          f"lengths={coarse.selected_length_mm:.9f},{fine.selected_length_mm:.9f}")


def test_duplicate_tool_skips_redundant_contours():
    copper = box(5, 5, 15, 10)
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.4), ToolSpec(0.4)],
                                  target_width_mm=0.4)
    first, second = plan.stages
    assert first.rings
    assert second.candidate_rings == first.candidate_rings
    assert second.candidate_length_mm > 0
    assert second.rings == ()
    assert second.selected_length_mm == 0
    assert second.residual_mm2 == first.residual_mm2


def test_small_cavity_rest_machining():
    copper = box(5, 5, 15, 15).difference(box(9.9, 9.9, 10.1, 10.1))
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.4), ToolSpec(0.15)],
                                  target_width_mm=0.4, critical_points=[(10, 10)])
    first, second = plan.stages
    assert second.candidate_rings == 2
    assert len(second.rings) == 1
    assert second.rings[0].newly_covered_probes == (0,)
    assert LinearRing(second.rings[0].coordinates).is_ccw
    assert not plan.uncovered_probe_indices
    print(f"multi-tool cavity: candidate fine length={second.candidate_length_mm:.9f}; "
          f"selected fine length={second.selected_length_mm:.9f}; "
          f"residual={plan.residual_mm2:.9f}")


def test_rejected_coarse_tool_does_not_discard_fine_stage():
    plan = plan_multi_tool_preview(box(0.3, 3, 4, 7), BOARD,
                                  [ToolSpec(0.4), ToolSpec(0.1)], target_width_mm=0.4)
    assert "leaves board" in plan.stages[0].rejection
    assert plan.stages[0].residual_mm2 == plan.target_mm2
    assert plan.stages[1].rejection is None and plan.stages[1].rings


def test_unreachable_probe_remains_reported():
    copper = box(3, 3, 7, 7).union(box(7.2, 3, 11, 7))
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.4)],
                                  target_width_mm=0.4, critical_points=[(7.1, 5)])
    assert plan.uncovered_probe_indices == (0,)


def test_critical_probe_overrides_area_filter():
    copper = box(3, 3, 7, 7).union(box(7.2, 3, 11, 7))
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.15)],
                                  target_width_mm=0.4, min_gain_mm2=100,
                                  critical_points=[(7.1, 5)])
    assert len(plan.stages[0].rings) == 1
    assert not plan.uncovered_probe_indices


def test_retains_direction_and_copper_clearance():
    copper = box(5, 5, 10, 10)
    plan = plan_multi_tool_preview(copper, BOARD, [ToolSpec(0.2, 3)],
                                  target_width_mm=0.6, clockwise=False)
    for stage in plan.stages:
        for ring in stage.rings:
            assert LinearRing(ring.coordinates).is_ccw
            assert LineString(ring.coordinates).distance(copper) >= 0.1
    assert [r.pass_index for r in plan.stages[0].rings] == [0, 1, 2]


@pytest.mark.parametrize("settings", [
    {"target_width_mm": 0}, {"target_width_mm": 0.4, "min_gain_mm2": -1},
    {"target_width_mm": 0.4, "critical_points": [(6, 6)]},
    {"target_width_mm": 0.4, "critical_points": [(float("nan"), 0)]},
])
def test_invalid_plan(settings):
    with pytest.raises(ValueError):
        plan_multi_tool_preview(box(5, 5, 10, 10), BOARD, [ToolSpec(0.4)], **settings)


@pytest.mark.parametrize("diameter,passes,overlap", [(0,1,0.2),(0.2,0,0.2),(0.2,1,1)])
def test_invalid_tool(diameter, passes, overlap):
    with pytest.raises(ValueError):
        ToolSpec(diameter, passes, overlap)
