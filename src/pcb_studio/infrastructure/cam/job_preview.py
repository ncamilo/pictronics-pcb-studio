"""Compose the experimental CAM engines without creating executable instructions."""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

from shapely.geometry import LineString
from pcb_studio.domain.pcb import BoardOutline, PCBProject, validate_xy
from pcb_studio.infrastructure.cam.geometry_comparison import (
    geometry_from_copper, geometry_from_outline,
)
from pcb_studio.infrastructure.cam.multi_tool_preview import (
    MultiToolPreview, ToolSpec, plan_multi_tool_preview,
)
from pcb_studio.infrastructure.cam.drilling_preview import (
    DrillingPreview, plan_drilling_preview,
)
from pcb_studio.infrastructure.cam.cutout_preview import (
    CutoutPreview, Tab, plan_cutout_preview,
)

Operation = Literal["isolation", "drill", "mill_slot", "cutout_internal", "cutout_external"]


@dataclass(frozen=True)
class JobStage:
    operation: Operation
    diameter_mm: float
    source_index: int | None
    feature_count: int
    cutting_xy_mm: float


@dataclass(frozen=True)
class JobDiagnostic:
    code: str
    detail: str


@dataclass(frozen=True)
class JobPreview:
    project_name: str
    copper_side: Literal["top", "bottom"]
    isolation: MultiToolPreview
    drilling: DrillingPreview
    cutout: CutoutPreview
    stages: tuple[JobStage, ...]
    diagnostics: tuple[JobDiagnostic, ...]

    @property
    def cutting_xy_mm(self):
        """Sum of nominal centerline cutting lengths, excluding Z and rapids."""
        return sum(s.cutting_xy_mm for s in self.stages)

    @property
    def manufacturing_ready(self):
        return False


def plan_job_preview(project: PCBProject, stock: BoardOutline, *,
                     isolation_tools: tuple[ToolSpec, ...],
                     target_width_mm: float, cutout_diameter_mm: float,
                     tabs: tuple[Tab, ...] = (), start=(0.0, 0.0),
                     clearance_mm=0.002, critical_points=(),
                     residual_report_threshold_mm2=1e-6):
    """Integrate one copper side in canonical XY, without transforms or motion.

    Return all geometric subplans or raise on invalid geometry. Rejected
    isolation candidates, incomplete coverage and duplicate drills remain
    explicit diagnostic findings, not a permission to execute. Stage indices
    refer to the unmodified isolation/drilling records. All cutouts precede
    no other operations except their own exterior phase. No depth, fixtures,
    actual tool assignment, time estimate, or machine connection.
    """
    if not isinstance(project, PCBProject) or not project.name.strip():
        raise ValueError("Expected named PCBProject")
    if project.outline is None:
        raise ValueError("Board outline required")
    if len(project.copper) != 1:
        raise ValueError("Job preview requires exactly one copper side")
    if not isinstance(stock, BoardOutline):
        raise ValueError("Explicit stock outline required")
    validate_xy(start)
    if (not isfinite(residual_report_threshold_mm2)
            or residual_report_threshold_mm2 < 0):
        raise ValueError("Invalid residual reporting threshold")
    tabs = tuple(tabs)
    board = geometry_from_outline(project.outline)
    copper = geometry_from_copper(project.copper[0])
    # Validate stock and all cutout paths up front. No partial object is returned.
    cutout = plan_cutout_preview(project.outline, stock, cutout_diameter_mm,
                                  tabs=tabs, margin_mm=clearance_mm)
    drilling = plan_drilling_preview(project.drills, project.outline,
                                      start=start, edge_clearance_mm=clearance_mm)
    isolation = plan_multi_tool_preview(
        copper, board, isolation_tools, target_width_mm=target_width_mm,
        clearance_mm=clearance_mm, critical_points=critical_points)
    stages = []
    diagnostics = []
    for i, s in enumerate(isolation.stages):
        if s.rejection is not None:
            diagnostics.append(JobDiagnostic("isolation_tool_rejected", f"Stage {i}: {s.rejection}"))
        elif s.rings:
            stages.append(JobStage("isolation", s.tool.diameter_mm, i,
                                   len(s.rings), s.selected_length_mm))
    if not stages:
        diagnostics.append(JobDiagnostic("no_isolation_paths", "No isolation contour selected"))
    if isolation.residual_mm2 > residual_report_threshold_mm2:
        diagnostics.append(JobDiagnostic("residual_isolation",
            f"{isolation.residual_mm2:.12g} mm2 above reporting threshold"))
    if isolation.uncovered_probe_indices:
        diagnostics.append(JobDiagnostic("uncovered_critical_points",
                                         str(isolation.uncovered_probe_indices)))
    for i, s in enumerate(drilling.stages):
        stages.append(JobStage(s.operation, s.diameter_mm, i,
                               len(s.features), s.cutting_xy_mm))
    if not drilling.stages:
        diagnostics.append(JobDiagnostic("no_drill_features", "No drills or slots in input"))
    if drilling.duplicate_features:
        diagnostics.append(JobDiagnostic("duplicate_drill_features",
                                         f"{len(drilling.duplicate_features)} duplicate pairs"))
    if cutout.internal_paths:
        stages.append(JobStage("cutout_internal", cutout.diameter_mm, None,
                               len(cutout.internal_paths),
                               sum(LineString(p).length for p in cutout.internal_paths)))
        diagnostics.append(JobDiagnostic("internal_slug_retention_unverified",
                                         "Internal waste retention not modeled"))
    stages.append(JobStage("cutout_external", cutout.diameter_mm, None,
                           len(cutout.exterior_paths),
                           sum(LineString(p).length for p in cutout.exterior_paths)))
    if not cutout.tab_gaps:
        diagnostics.append(JobDiagnostic("no_external_tabs", "No external bridge specified"))
    return JobPreview(project.name, project.copper[0].side, isolation, drilling,
                      cutout, tuple(stages), tuple(diagnostics))
