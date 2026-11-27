"""Ordered polarity composition with bounded batches of same-polarity shapes."""
from itertools import groupby
from numpy import isfinite
from shapely import get_coordinates, union_all
from shapely.geometry import GeometryCollection

BATCH_SIZE = 2048


def _validated(operations):
    for geometry, dark in operations:
        if (type(dark) is not bool or geometry.geom_type not in ("Polygon", "MultiPolygon")
                or geometry.is_empty or not geometry.is_valid or geometry.has_z
                or not isfinite(get_coordinates(geometry)).all()):
            raise ValueError("Invalid copper operation")
        yield geometry, dark


def compose_copper(operations):
    """Union consecutive dark operations; subtract consecutive clear operations.

    Never reorder across a polarity change. No coordinate snapping, rounding,
    simplification or validity repair. GEOS overlay order can change rounding.
    """
    from itertools import islice
    copper = GeometryCollection()
    for dark, run in groupby(_validated(operations), key=lambda item: item[1]):
        while batch := list(islice(run, BATCH_SIZE)):
            shapes = [g for g, _ in batch]
            merged = shapes[0] if len(shapes) == 1 else union_all(shapes)
            if not merged.is_valid:
                raise ValueError("Invalid batch geometry")
            if dark:
                copper = merged if copper.is_empty else copper.union(merged)
            elif not copper.is_empty:
                copper = copper.difference(merged)
            if not copper.is_valid:
                raise ValueError("Invalid composed geometry")
    return copper
