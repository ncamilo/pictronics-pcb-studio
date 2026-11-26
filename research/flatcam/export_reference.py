"""Executed only inside the pinned upstream FlatCAM pytest environment."""
import json
import os
from pathlib import Path

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from appParsers.ParseGerber import Gerber
from appParsers.ParseExcellon import Excellon
from tests.helpers_objects import _headless_qt, make_app_0b


def polygons(value):
    if isinstance(value, (Polygon, MultiPolygon)):
        assert not value.is_empty and value.is_valid
        yield value
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from polygons(item)
    else:
        raise AssertionError(f"Unexpected reference geometry {type(value)}")


def test_export_reference():
    source = Path(os.environ["PCB_REFERENCE_FIXTURE"])
    app = make_app_0b(gerber_simplification=False, gerber_circle_steps=256)
    gerber = Gerber(app)
    assert gerber.parse_file(str(source / "bottom.gbr")) is None
    assert gerber.units.upper() == "MM"
    copper = unary_union(list(polygons(gerber.solid_geometry)))
    assert copper.is_valid and not copper.is_empty

    excellon = Excellon(app)
    assert excellon.parse_file(str(source / "drills.drl")) is None
    assert excellon.units.upper() == "MM"
    drills = sorted([p.x, p.y, tool["tooldia"]]
                    for tool in excellon.tools.values() for p in tool["drills"])
    slots = sorted([a.x, a.y, b.x, b.y, tool["tooldia"]]
                   for tool in excellon.tools.values() for a, b in tool["slots"])
    result = {"units": "mm", "copper_wkb_hex": copper.wkb_hex,
              "drills": drills, "slots": slots,
              "options": {"gerber_simplification": False, "gerber_circle_steps": 256}}
    Path(os.environ["PCB_REFERENCE_RESULT"]).write_text(json.dumps(result, indent=2),
                                                       encoding="utf-8")
