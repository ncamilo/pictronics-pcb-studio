"""Experimental ordered composition of already normalized copper polygons."""
from shapely.geometry import GeometryCollection


def compose_copper(operations):
    """Apply (geometry, dark: bool) pairs in file order, starting with empty copper.

    Input must be valid, finite 2D polygonal geometry in mm.
    This is not a Gerber parser, aperture renderer or production CAM validator.
    """
    from math import isfinite
    from shapely import get_coordinates

    copper = GeometryCollection()
    for geometry, dark in operations:
        if (type(dark) is not bool or geometry.geom_type not in ("Polygon", "MultiPolygon")
                or geometry.is_empty or not geometry.is_valid or geometry.has_z
                or not all(isfinite(v) for point in get_coordinates(geometry) for v in point)):
            raise ValueError("Invalid copper operation")
        copper = copper.union(geometry) if dark else copper.difference(geometry)
        if not copper.is_valid:
            raise ValueError("Invalid composed geometry")
    return copper
