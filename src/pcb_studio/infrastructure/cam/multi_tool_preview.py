"""Experimental residual-aware isolation planning. No executable machine commands."""
from dataclasses import dataclass
from math import isclose, isfinite

from shapely.geometry import LineString, Point
from pcb_studio.infrastructure.cam.isolation_preview import (
    _polygonal, generate_isolation_preview,
)

XY = tuple[float, float]
PathXY = tuple[XY, ...]


@dataclass(frozen=True)
class ToolSpec:
    diameter_mm: float
    passes: int = 1
    overlap: float = 0.2

    def __post_init__(self):
        if (not isfinite(self.diameter_mm) or self.diameter_mm <= 0
                or type(self.passes) is not int or not 1 <= self.passes <= 100
                or not isfinite(self.overlap) or not 0 <= self.overlap < 1):
            raise ValueError("Invalid tool settings")


@dataclass(frozen=True)
class SelectedRing:
    pass_index: int
    coordinates: PathXY
    new_area_mm2: float
    newly_covered_probes: tuple[int, ...]


@dataclass(frozen=True)
class ToolStage:
    tool: ToolSpec
    rings: tuple[SelectedRing, ...]
    candidate_rings: int
    candidate_length_mm: float
    selected_length_mm: float
    new_area_mm2: float
    residual_mm2: float
    rejection: str | None = None


@dataclass(frozen=True)
class MultiToolPreview:
    target_mm2: float
    covered_mm2: float
    residual_mm2: float
    residual_wkb_hex: str
    stages: tuple[ToolStage, ...]
    uncovered_probe_indices: tuple[int, ...]

    @property
    def coverage_fraction(self):
        return 1 - self.residual_mm2 / self.target_mm2

    @property
    def manufacturing_ready(self):
        return False


def plan_multi_tool_preview(copper, board, tools, *, target_width_mm,
                            clearance_mm=0.002, min_gain_mm2=1e-5,
                            critical_points=(), clockwise=True):
    """Keep whole validated rings that reach residual area or a requested probe.

    Tools execute in supplied order. A geometrically rejected candidate is
    recorded and skipped. A ring is not trimmed, reversed, or connected to
    another ring. Nominal swept areas are approximate, not measured cutting.
    Critical points are explicit diagnostics, not automatically inferred nets.
    """
    _polygonal(copper)
    _polygonal(board)
    tools = tuple(tools)
    if not tools or any(not isinstance(t, ToolSpec) for t in tools):
        raise ValueError("Expected one or more ToolSpec entries")
    if not board.covers(copper):
        raise ValueError("Copper outside board material")
    if (not all(isfinite(v) for v in (target_width_mm, clearance_mm, min_gain_mm2))
            or not 0 < clearance_mm < target_width_mm or min_gain_mm2 < 0
            or type(clockwise) is not bool):
        raise ValueError("Invalid plan settings")
    target = copper.buffer(target_width_mm, quad_segs=64).difference(
        copper.buffer(clearance_mm, quad_segs=64)).intersection(board)
    if target.is_empty or not target.is_valid or not isfinite(target.area) or target.area <= 0:
        raise ValueError("Empty or invalid isolation target")
    probes = []
    for xy in critical_points:
        if len(xy) != 2 or not all(isfinite(v) for v in xy):
            raise ValueError("Invalid critical point")
        point = Point(*xy)
        if not target.covers(point):
            raise ValueError("Critical point outside isolation target")
        probes.append(point)

    residual = target
    missing = set(range(len(probes)))
    stages = []
    for tool in tools:
        before = residual.area
        try:
            previews = generate_isolation_preview(
                copper, board, tool.diameter_mm, passes=tool.passes,
                overlap=tool.overlap, clearance_mm=clearance_mm, clockwise=clockwise)
        except ValueError as exc:
            stages.append(ToolStage(tool, (), 0, 0.0, 0.0, 0.0, before, str(exc)))
            continue
        selected = []
        candidate_count = 0
        candidate_length = selected_length = 0.0
        for p in previews:
            for path in p.paths:
                line = LineString(path)
                candidate_count += 1
                candidate_length += line.length
                swept = line.buffer(tool.diameter_mm / 2, quad_segs=64)
                gain = residual.intersection(swept).area
                reached = tuple(i for i in sorted(missing) if swept.covers(probes[i]))
                if gain <= min_gain_mm2 and not reached:
                    continue
                after = residual.difference(swept)
                if (not after.is_valid or not isfinite(after.area) or not isfinite(gain)
                        or not isclose(after.area + gain, residual.area,
                                       rel_tol=1e-9, abs_tol=1e-10)):
                    raise ValueError("Invalid residual area partition")
                selected.append(SelectedRing(p.index, path, gain, reached))
                selected_length += line.length
                residual = after
                missing.difference_update(reached)
        stages.append(ToolStage(tool, tuple(selected), candidate_count,
                                candidate_length, selected_length,
                                max(0.0, before - residual.area), residual.area))
    if residual.area > target.area and not isclose(residual.area, target.area,
                                                  rel_tol=1e-9, abs_tol=0):
        raise ValueError("Residual exceeds target")
    if residual.area > target.area:
        # GEOS roundoff only. Keep the original target geometry and area.
        residual = target
    return MultiToolPreview(target.area, target.area - residual.area, residual.area,
                            residual.wkb_hex, tuple(stages), tuple(sorted(missing)))
