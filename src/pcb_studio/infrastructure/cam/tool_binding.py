"""Bind explicit nominal tool IDs to preview stages; no machine commands."""
from dataclasses import dataclass
from math import isclose

from pcb_studio.domain.tools import CuttingTool, ProcessSettings, ToolLibrary, validate_operation
from pcb_studio.infrastructure.cam.job_preview import JobPreview, JobStage
from pcb_studio.infrastructure.cam.multi_tool_preview import ToolSpec


@dataclass(frozen=True)
class ToolSelection:
    tool_id: str
    settings: ProcessSettings

    def __post_init__(self):
        if not isinstance(self.tool_id, str) or not self.tool_id.strip():
            raise ValueError("Explicit tool ID required")
        if not isinstance(self.settings, ProcessSettings):
            raise ValueError("Explicit process settings required")


@dataclass(frozen=True)
class BoundStage:
    stage: JobStage
    tool: CuttingTool
    settings: ProcessSettings
    effective_diameter_mm: float


@dataclass(frozen=True)
class BoundJobPreview:
    job: JobPreview
    stages: tuple[BoundStage, ...]

    @property
    def manufacturing_ready(self):
        return False


def isolation_tool_spec(library: ToolLibrary, selection: ToolSelection, *,
                        passes=1, overlap=0.2):
    """Resolve the ideal isolation diameter before generating the geometry."""
    tool = library.get(selection.tool_id)
    diameter = validate_operation(tool, "isolation", selection.settings)
    return ToolSpec(diameter, passes, overlap)


def bind_job_tools(job: JobPreview, library: ToolLibrary, selections):
    """One explicit selection per actual stage in order; no implicit size rounding.

    A changed effective diameter requires regenerated geometry, not merely a
    different label. The 1e-9 mm absolute tolerance is numerical only.
    Preserve every job diagnostic. No actual machine profile or hardware check.
    """
    if not isinstance(job, JobPreview):
        raise ValueError("Expected JobPreview")
    selections = tuple(selections)
    if len(selections) != len(job.stages):
        raise ValueError("One tool selection per job stage required")
    bound = []
    for stage, selection in zip(job.stages, selections):
        if not isinstance(selection, ToolSelection):
            raise ValueError("Expected ToolSelection")
        tool = library.get(selection.tool_id)
        diameter = validate_operation(tool, stage.operation, selection.settings)
        if not isclose(diameter, stage.diameter_mm, rel_tol=0, abs_tol=1e-9):
            raise ValueError("Effective diameter differs from planned geometry; regenerate")
        bound.append(BoundStage(stage, tool, selection.settings, diameter))
    return BoundJobPreview(job, tuple(bound))
