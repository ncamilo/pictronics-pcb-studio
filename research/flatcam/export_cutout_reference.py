"""Run the original FlatCAM contour offset and tab splitting functions."""
import json
import os
from pathlib import Path

from shapely.geometry import Polygon, LineString
from appPlugins.ToolCutOut.CutOutGen import Contour, offset_contours, any_cutout_handler


def serialize(paths):
    return [LineString(p.coords).wkb_hex for p in paths]


def test_export_cutout():
    data = json.loads(Path(os.environ["PCB_CUTOUT_CASES"]).read_text())
    output = []
    for case in data["cases"]:
        dia = case["diameter"]
        # Canonical edge centerlines: zero stroke width, identical input.
        contours = [Contour(Polygon(case["outer"]), 0, "outer", 0, 0)]
        contours += [Contour(Polygon(h), 1, "inner", i+1, 0)
                     for i,h in enumerate(case["holes"])]
        paths = offset_contours(contours, data["margin"], dia/2, "gerber")
        assert len(paths[0]) == 1
        outside = LineString(paths[0][0].coords)
        internal = [p for group in paths[1:] for p in group]
        cut, gaps = any_cutout_handler(outside, dia, case["mode"],
                                      data["tab_width"]+dia, data["margin"])
        output.append({"name":case["name"], "full":outside.wkb_hex,
                       "external":serialize(cut), "internal":serialize(internal),
                       "gaps":serialize(gaps), "inner_counts":[len(g) for g in paths[1:]]})
    Path(os.environ["PCB_CUTOUT_RESULT"]).write_text(json.dumps(output), encoding="utf-8")
