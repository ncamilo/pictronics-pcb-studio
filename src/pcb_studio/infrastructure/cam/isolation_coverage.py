"""Planar coverage diagnostics; never a manufacturing authorization."""
from dataclasses import dataclass
from math import isfinite

from shapely.geometry import LineString
from shapely.ops import unary_union

from pcb_studio.infrastructure.cam.isolation_preview import (
    _polygonal, generate_isolation_preview,
)


@dataclass(frozen=True)
class CoverageReport:
    target_mm2: float
    covered_mm2: float
    residual_mm2: float
    coverage_fraction: float
    residual_wkb_hex: str
    merged_passes: tuple[int, ...]
    disappeared_hole_passes: tuple[int, ...]


@dataclass(frozen=True)
class ToolEvaluation:
    diameter_mm: float
    coverage: CoverageReport | None
    rejection: str | None


def measure_isolation(copper, board, diameter_mm, *, target_width_mm,
                      passes=1, overlap=0.2, clearance_mm=0.002):
    """Measure the same explicit band for every candidate tool.

    Target is board material within target_width of copper, excluding the
    requested clearance band. Coverage is the polygonal approximation of
    the XY swept disk clipped to that target. It does not model physical
    copper removal, electrical nets, Z motion or tool/runout errors.
    """
    original = _polygonal(copper)
    _polygonal(board)
    if (not isfinite(target_width_mm) or not isfinite(clearance_mm)
            or not 0 < clearance_mm < target_width_mm):
        raise ValueError("Target width must exceed positive clearance")
    previews = generate_isolation_preview(
        copper, board, diameter_mm, passes=passes,
        overlap=overlap, clearance_mm=clearance_mm)
    target = copper.buffer(target_width_mm, quad_segs=64).difference(
        copper.buffer(clearance_mm, quad_segs=64)).intersection(board)
    if target.is_empty or not target.is_valid or not isfinite(target.area) or target.area <= 0:
        raise ValueError("Empty or invalid isolation target")

    # Nominal radius for coverage, not inflated safety-check radius.
    swept = unary_union([LineString(path).buffer(diameter_mm / 2, quad_segs=64)
                         for p in previews for path in p.paths])
    covered = target.intersection(swept)
    residual = target.difference(swept)
    if not covered.is_valid or not residual.is_valid:
        raise ValueError("Invalid coverage result")
    original_holes = sum(len(p.interiors) for p in original)
    vanished = []
    for p in previews:
        # Reconstruct the envelope using the same approximation; track
        # disappearance of interior rings as an additional diagnostic.
        envelope = _polygonal(copper.buffer(p.offset_mm, quad_segs=64))
        if sum(len(poly.interiors) for poly in envelope) < original_holes:
            vanished.append(p.index)
    return CoverageReport(
        target.area, covered.area, residual.area, covered.area / target.area,
        residual.wkb_hex, tuple(p.index for p in previews if p.merged_components),
        tuple(vanished))


def evaluate_tools(copper, board, diameters_mm, *, target_width_mm,
                   passes=1, overlap=0.2, clearance_mm=0.002):
    """Evaluate candidates in supplied order, without selecting a physical tool.

    Rejected candidates retain their reason. Same pass count does not imply
    equal machining time. No ranking or automatic manufacture approval.
    """
    _polygonal(copper)
    _polygonal(board)
    if (not isfinite(target_width_mm) or not isfinite(clearance_mm)
            or not 0 < clearance_mm < target_width_mm):
        raise ValueError("Target width must exceed positive clearance")
    if (type(passes) is not int or not 1 <= passes <= 100
            or not isfinite(overlap) or not 0 <= overlap < 1):
        raise ValueError("Invalid common isolation settings")
    results = []
    for diameter in diameters_mm:
        if not isfinite(diameter) or diameter <= 0:
            raise ValueError("Invalid candidate diameter")
        try:
            coverage = measure_isolation(
                copper, board, diameter, target_width_mm=target_width_mm,
                passes=passes, overlap=overlap, clearance_mm=clearance_mm)
        except ValueError as exc:
            results.append(ToolEvaluation(diameter, None, str(exc)))
        else:
            results.append(ToolEvaluation(diameter, coverage, None))
    return tuple(results)
