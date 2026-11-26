"""Immutable nominal tool geometry and separate experimental process settings."""
from dataclasses import dataclass
from math import isfinite, radians, tan
from typing import Literal

ToolKind = Literal["v_bit", "drill", "end_mill"]
Operation = Literal["isolation", "drill", "mill_slot", "cutout_internal", "cutout_external"]


def _number(value):
    return type(value) in (int, float) and isfinite(value)


@dataclass(frozen=True)
class CuttingTool:
    tool_id: str
    name: str
    kind: ToolKind
    diameter_mm: float
    cutting_length_mm: float
    tip_mm: float | None = None
    angle_deg: float | None = None

    def __post_init__(self):
        if (not isinstance(self.tool_id, str) or not self.tool_id.strip()
                or self.tool_id != self.tool_id.strip()
                or not isinstance(self.name, str) or not self.name.strip()
                or self.kind not in ("v_bit", "drill", "end_mill")
                or not all(_number(v) and v > 0
                           for v in (self.diameter_mm, self.cutting_length_mm))):
            raise ValueError("Invalid nominal tool geometry")
        if self.kind == "v_bit":
            if (not _number(self.tip_mm) or not 0 <= self.tip_mm < self.diameter_mm
                    or not _number(self.angle_deg) or not 0 < self.angle_deg < 180):
                raise ValueError("Invalid V-bit geometry")
        elif self.tip_mm is not None or self.angle_deg is not None:
            raise ValueError("Tip and angle are exclusive to V-bits")

    def effective_diameter(self, depth_mm):
        """Ideal maximum width at a positive depth; no extrapolation past geometry."""
        if not _number(depth_mm) or not 0 < depth_mm <= self.cutting_length_mm:
            raise ValueError("Depth exceeds nominal cutting length or is invalid")
        if self.kind != "v_bit":
            return self.diameter_mm
        width = self.tip_mm + 2 * depth_mm * tan(radians(self.angle_deg / 2))
        if not isfinite(width) or not 0 < width <= self.diameter_mm:
            raise ValueError("V-bit depth exceeds modeled cone diameter")
        return width

    def supports(self, operation: Operation):
        if operation == "isolation":
            return self.kind in ("v_bit", "end_mill")
        if operation == "drill":
            return self.kind == "drill"
        if operation in ("mill_slot", "cutout_internal", "cutout_external"):
            return self.kind == "end_mill"
        return False


@dataclass(frozen=True)
class ProcessSettings:
    """Explicit positive magnitudes; no machine defaults or calibration claims."""
    depth_mm: float
    max_stepdown_mm: float
    plunge_mm_min: float
    spindle_rpm: int
    feed_xy_mm_min: float | None = None

    def __post_init__(self):
        if (not all(_number(v) and v > 0 for v in
                    (self.depth_mm, self.max_stepdown_mm, self.plunge_mm_min))
                or self.max_stepdown_mm > self.depth_mm
                or type(self.spindle_rpm) is not int or self.spindle_rpm <= 0
                or (self.feed_xy_mm_min is not None and
                    (not _number(self.feed_xy_mm_min) or self.feed_xy_mm_min <= 0))):
            raise ValueError("Invalid process settings")


@dataclass(frozen=True)
class ToolLibrary:
    tools: tuple[CuttingTool, ...]

    def __post_init__(self):
        if (type(self.tools) is not tuple or not self.tools
                or any(not isinstance(t, CuttingTool) for t in self.tools)):
            raise ValueError("Expected immutable nonempty tool library")
        ids = [t.tool_id for t in self.tools]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate tool ID")

    def get(self, tool_id: str):
        for tool in self.tools:
            if tool.tool_id == tool_id:
                return tool
        raise ValueError(f"Unknown tool ID: {tool_id}")


def validate_operation(tool: CuttingTool, operation: Operation, settings: ProcessSettings):
    """Return ideal diameter for the operation, not machining authorization."""
    if not tool.supports(operation):
        raise ValueError(f"Tool {tool.tool_id} incompatible with {operation}")
    if operation == "drill":
        if settings.feed_xy_mm_min is not None:
            raise ValueError("Drill operation cannot specify lateral cutting feed")
    elif settings.feed_xy_mm_min is None:
        raise ValueError("Milling operation requires lateral feed")
    # Changing depth changes the V-bit footprint; do not silently reuse
    # a final-depth contour for different depths.
    if tool.kind == "v_bit" and settings.max_stepdown_mm != settings.depth_mm:
        raise ValueError("V-bit multi-depth planning not supported")
    return tool.effective_diameter(settings.depth_mm)
