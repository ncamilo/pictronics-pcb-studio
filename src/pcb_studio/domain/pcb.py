"""Canonical, immutable preview model. All lengths are millimetres."""
from dataclasses import dataclass
from math import isfinite
from typing import Literal

XY = tuple[float, float]
Ring = tuple[XY, ...]


def validate_xy(point: XY) -> None:
    if len(point) != 2 or not all(isfinite(v) for v in point):
        raise ValueError("Expected finite XY coordinates")


def validate_ring(ring: Ring) -> None:
    for point in ring:
        validate_xy(point)
    if len(ring) < 4 or ring[0] != ring[-1] or len(set(ring[:-1])) < 3:
        raise ValueError("Expected a closed ring with at least three vertices")


@dataclass(frozen=True)
class CopperPolygon:
    exterior: Ring
    holes: tuple[Ring, ...] = ()

    def __post_init__(self):
        validate_ring(self.exterior)
        for ring in self.holes:
            validate_ring(ring)


@dataclass(frozen=True)
class CopperLayer:
    source: str
    side: Literal["top", "bottom"]
    polygons: tuple[CopperPolygon, ...]

    def __post_init__(self):
        if self.side not in ("top", "bottom"):
            raise ValueError("Copper side must be explicit")


@dataclass(frozen=True)
class Drill:
    center: XY
    diameter_mm: float
    plated: bool | None = None

    def __post_init__(self):
        validate_xy(self.center)
        if not isfinite(self.diameter_mm) or self.diameter_mm <= 0:
            raise ValueError("Invalid drill diameter")


@dataclass(frozen=True)
class Slot:
    start: XY
    end: XY
    diameter_mm: float
    plated: bool | None = None

    def __post_init__(self):
        validate_xy(self.start)
        validate_xy(self.end)
        if self.start == self.end or not isfinite(self.diameter_mm) or self.diameter_mm <= 0:
            raise ValueError("Invalid straight slot")


@dataclass(frozen=True)
class DrillLayer:
    source: str
    drills: tuple[Drill, ...] = ()
    slots: tuple[Slot, ...] = ()


@dataclass(frozen=True)
class BoardOutline:
    source: str
    exterior: Ring

    def __post_init__(self):
        validate_ring(self.exterior)


@dataclass(frozen=True)
class PCBProject:
    name: str
    copper: tuple[CopperLayer, ...]
    drills: tuple[DrillLayer, ...] = ()
    outline: BoardOutline | None = None
    # Preview only until full parser coverage and CAM validation are implemented.
    @property
    def manufacturing_ready(self) -> bool:
        return False
