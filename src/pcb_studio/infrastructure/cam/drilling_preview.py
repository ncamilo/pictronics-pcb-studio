"""Read-only drilling and straight-slot planning in canonical board XY millimetres."""
from dataclasses import dataclass
from math import dist, isfinite
from typing import Literal

from shapely.geometry import Point, LineString
from pcb_studio.domain.pcb import Drill, DrillLayer, Slot, BoardOutline, validate_xy
from pcb_studio.infrastructure.cam.geometry_comparison import geometry_from_outline
from pcb_studio.infrastructure.cam.isolation_preview import _polygonal
from pcb_studio.infrastructure.cam.path_optimizer import optimize_drills

XY = tuple[float, float]


@dataclass(frozen=True)
class FeatureRef:
    layer_index: int
    source: str
    feature_index: int
    feature: Drill | Slot


@dataclass(frozen=True)
class DrillStage:
    operation: Literal["drill", "mill_slot"]
    diameter_mm: float
    features: tuple[FeatureRef, ...]
    input_rapid_mm: float
    planned_rapid_mm: float
    cutting_xy_mm: float


@dataclass(frozen=True)
class DrillingPreview:
    stages: tuple[DrillStage, ...]
    duplicate_features: tuple[tuple[FeatureRef, FeatureRef], ...]

    @property
    def manufacturing_ready(self):
        return False


def _travel(features, start):
    total = 0.0
    current = start
    for ref in features:
        f = ref.feature
        entry, exit_point = (f.center, f.center) if isinstance(f, Drill) else (f.start, f.end)
        total += dist(current, entry)
        current = exit_point
    return total


def plan_drilling_preview(layers, outline: BoardOutline, *, start=(0.0, 0.0),
                          edge_clearance_mm=0.002, optimize=True):
    """Group exactly equal nominal sizes by operation, keeping source and plating.

    Each stage's travel starts at the supplied common XY point; inter-stage
    positioning, Z, tool changes and fixtures are not modeled. Slots retain
    their source direction and order. Exact duplicate geometry is reported,
    never silently deduplicated. No physical tool assignment or G-code.
    """
    validate_xy(start)
    if not isfinite(edge_clearance_mm) or edge_clearance_mm < 0 or type(optimize) is not bool:
        raise ValueError("Invalid drilling preview settings")
    board = geometry_from_outline(outline)
    _polygonal(board)
    groups = {}
    seen = {}
    duplicates = []
    for li, layer in enumerate(layers):
        if not isinstance(layer, DrillLayer):
            raise ValueError("Expected DrillLayer")
        for operation, features, expected in (("drill", layer.drills, Drill),
                                              ("mill_slot", layer.slots, Slot)):
            for fi, f in enumerate(features):
                if not isinstance(f, expected):
                    raise ValueError("Invalid feature type")
                ref = FeatureRef(li, layer.source, fi, f)
                if isinstance(f, Drill):
                    validate_xy(f.center)
                    centerline = Point(f.center)
                    key = (operation, f.diameter_mm, tuple(f.center))
                else:
                    validate_xy(f.start)
                    validate_xy(f.end)
                    if f.start == f.end:
                        raise ValueError("Zero-length slot")
                    centerline = LineString([f.start, f.end])
                    key = (operation, f.diameter_mm, *sorted((tuple(f.start), tuple(f.end))))
                if not isfinite(f.diameter_mm) or f.diameter_mm <= 0:
                    raise ValueError("Invalid nominal diameter")
                # Distance to all board boundaries, including cutouts,
                # tests the nominal swept disk without tessellating it.
                required = f.diameter_mm / 2 + edge_clearance_mm
                if not board.covers(centerline) or centerline.distance(board.boundary) < required:
                    raise ValueError(f"Feature outside board clearance: {layer.source} {operation} {fi}")
                if key in seen:
                    duplicates.append((seen[key], ref))
                else:
                    seen[key] = ref
                groups.setdefault((operation, f.diameter_mm), []).append(ref)
    stages = []
    for (operation, diameter), refs in sorted(groups.items()):
        baseline = _travel(refs, start)
        ordered = refs
        if operation == "drill" and optimize:
            indices = optimize_drills([r.feature.center for r in refs], start=start)
            candidate = [refs[i] for i in indices]
            if _travel(candidate, start) <= baseline:
                ordered = candidate
        cutting = sum(dist(r.feature.start, r.feature.end) for r in ordered) if operation == "mill_slot" else 0.0
        stages.append(DrillStage(operation, diameter, tuple(ordered), baseline,
                                 _travel(ordered, start), cutting))
    return DrillingPreview(tuple(stages), tuple(duplicates))
