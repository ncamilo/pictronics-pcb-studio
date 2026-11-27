"""Nominal workpiece Z coordinates for offline simulation only."""
from dataclasses import dataclass
from math import ceil, isfinite


def _finite(value):
    return type(value) in (int, float) and isfinite(value)


@dataclass(frozen=True)
class DepthSetup:
    thickness_mm: float
    safe_z_mm: float
    breakthrough_limit_mm: float

    def __post_init__(self):
        if (not all(_finite(v) for v in (self.thickness_mm, self.safe_z_mm,
                                         self.breakthrough_limit_mm))
                or self.thickness_mm <= 0 or self.safe_z_mm <= 0
                or self.breakthrough_limit_mm < 0
                or not isfinite(self.thickness_mm + self.breakthrough_limit_mm)):
            raise ValueError("Invalid simulation depth setup")


def depth_levels(depth_mm, max_stepdown_mm):
    """Equal increments not exceeding the requested maximum; final Z exact."""
    if (not all(_finite(v) and v > 0 for v in (depth_mm,max_stepdown_mm))
            or max_stepdown_mm > depth_mm):
        raise ValueError("Invalid depth increment")
    ratio = depth_mm / max_stepdown_mm
    if not isfinite(ratio) or ratio > 10000:
        raise ValueError("Too many depth levels for preview")
    n = ceil(ratio)
    levels = tuple(-depth_mm * (i/n) for i in range(1,n)) + (-depth_mm,)
    return levels


def validate_depth(operation, depth_mm, setup: DepthSetup):
    if not _finite(depth_mm) or depth_mm <= 0:
        raise ValueError("Invalid depth")
    if operation == "isolation":
        if depth_mm >= setup.thickness_mm:
            raise ValueError("Isolation depth must be less than stock thickness")
    elif operation in ("drill","mill_slot","cutout_internal","cutout_external"):
        if not setup.thickness_mm <= depth_mm <= setup.thickness_mm + setup.breakthrough_limit_mm:
            raise ValueError("Through-cut depth outside explicit stock/breakthrough interval")
    else:
        raise ValueError("Unknown operation")
