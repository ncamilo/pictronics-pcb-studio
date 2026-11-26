"""Pure-domain tool validation and JSON round trips."""
import math
from pathlib import Path
from dataclasses import replace
import pytest
from pcb_studio.domain.tools import CuttingTool, ToolLibrary, ProcessSettings, validate_operation
from pcb_studio.infrastructure.cam.tool_library_io import load_tool_library, tool_library_json

V = CuttingTool("v","V","v_bit",3.175,1,0.1,30)
D = CuttingTool("d","D","drill",1,3)
E = CuttingTool("e","E","end_mill",1,3)
MILL = ProcessSettings(0.1,0.1,30,10000,100)
DRILL = ProcessSettings(1.6,0.8,30,10000)


def test_v_diameter_and_limits():
    assert V.effective_diameter(0.1) == pytest.approx(0.1+0.2*math.tan(math.pi/12))
    assert validate_operation(V,"isolation",MILL) == pytest.approx(0.15358983848622455)
    with pytest.raises(ValueError):
        replace(V,diameter_mm=0.12).effective_diameter(0.1)
    with pytest.raises(ValueError):
        V.effective_diameter(1.1)


@pytest.mark.parametrize("operation,tool,settings",[
    ("mill_slot",D,MILL),("cutout_external",D,MILL),
    ("drill",E,DRILL),("drill",V,DRILL),("mill_slot",V,MILL),
    ("isolation",D,MILL),("isolation",E,DRILL),("drill",D,MILL),
])
def test_incompatible_operation(operation,tool,settings):
    with pytest.raises(ValueError):
        validate_operation(tool,operation,settings)


def test_equal_diameter_distinct_tools():
    lib=ToolLibrary((D,E))
    assert lib.get("d") != lib.get("e")
    assert validate_operation(D,"drill",DRILL)==1
    assert validate_operation(E,"mill_slot",MILL)==1
    with pytest.raises(ValueError):
        lib.get("missing")
    with pytest.raises(ValueError):
        ToolLibrary((D,D))


@pytest.mark.parametrize("changes",[
    {"diameter_mm":0},{"cutting_length_mm":float("nan")},{"kind":"unknown"},
    {"angle_deg":30},{"tool_id":" "},{"diameter_mm":True}
])
def test_invalid_tool(changes):
    with pytest.raises(ValueError):
        replace(D,**changes)


@pytest.mark.parametrize("changes",[
    {"depth_mm":-1},{"max_stepdown_mm":0.2},{"plunge_mm_min":0},
    {"spindle_rpm":0},{"feed_xy_mm_min":float("inf")},{"spindle_rpm":True}
])
def test_invalid_settings(changes):
    with pytest.raises(ValueError):
        replace(MILL,**changes)


def test_v_multidepth_rejected():
    with pytest.raises(ValueError,match="multi-depth"):
        validate_operation(V,"isolation",replace(MILL,max_stepdown_mm=0.05))


def test_library_fixture_and_round_trip(tmp_path):
    root=Path(__file__).resolve().parents[1]/"examples"/"tool_library"/"nominal_tools.json"
    lib=load_tool_library(root)
    assert len(lib.tools)==4
    path=tmp_path/"tools.json"
    path.write_text(tool_library_json(lib),encoding="utf-8")
    assert load_tool_library(path)==lib


@pytest.mark.parametrize("payload",[
    '{"schema_version":2,"tools":[]}',
    '{"schema_version":1,"schema_version":1,"tools":[]}',
    '{"schema_version":1,"tools":[{"extra":1}]}',
    '{"schema_version":true,"tools":[]}',
])
def test_bad_library_json(tmp_path,payload):
    path=tmp_path/"tools.json"
    path.write_text(payload,encoding="utf-8")
    with pytest.raises(ValueError):
        load_tool_library(path)
