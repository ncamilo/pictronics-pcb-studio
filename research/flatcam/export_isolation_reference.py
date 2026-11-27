"""Run the original FlatCAM offset engine inside its own pytest environment."""
import json
import os
from pathlib import Path

from shapely.geometry import Polygon, MultiPolygon, LineString, box
from shapely.ops import unary_union
from appParsers.ParseGerber import Gerber
from appPlugins.ToolIsolation.IsolationGen import generate_envelope, pass_offset
from tests.helpers_objects import _headless_qt, make_app_0b


def rings(value):
    if isinstance(value, Polygon):
        yield LineString(value.exterior.coords)
        for hole in value.interiors:
            yield LineString(hole.coords)
    elif isinstance(value, MultiPolygon):
        for poly in value.geoms:
            yield from rings(poly)
    elif isinstance(value, (list, tuple)):
        for poly in value:
            yield from rings(poly)
    else:
        raise AssertionError(f"Unexpected envelope: {type(value)}")


def test_export_isolation():
    cases = json.loads(Path(os.environ["PCB_ISOLATION_CASES"]).read_text())
    app = make_app_0b(gerber_simplification=False)
    gerber = Gerber(app)
    gerber.units = "MM"
    gerber.geo_steps_per_circle = 256
    output = []
    for case in cases:
        copper = unary_union([box(*r) for r in case["rectangles"]])
        for hole in case["holes"]:
            copper = copper.difference(box(*hole))
        dia, overlap = case["diameter"], case["overlap"]
        passes = []
        for i in range(case["passes"]):
            matched = dia / 2 + 0.002 + i * dia * (1-overlap)
            native = pass_offset(dia, i, overlap)
            row = {"matched_offset_mm": matched, "native_offset_mm": native}
            for label, offset in (("matched", matched), ("native", native)):
                result = generate_envelope(gerber, offset, False, geometry=copper,
                                           env_iso_type=2, nr_passes=i)
                paths = list(rings(result))
                assert paths and all(p.is_ring for p in paths)
                row[label] = [p.wkb_hex for p in paths]
            passes.append(row)
        output.append({"name": case["name"], "copper_wkb_hex": copper.wkb_hex,
                       "passes": passes})
    Path(os.environ["PCB_ISOLATION_RESULT"]).write_text(json.dumps(output), encoding="utf-8")
