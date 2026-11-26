import json
import re
import xml.etree.ElementTree as ET
import pytest
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
from pcb_studio.infrastructure.cam.gcode_preview import render_gcode_preview
from pcb_studio.infrastructure.cam.gcode_readback import read_gcode_preview
from pcb_studio.infrastructure.cam.gcode_viewer import viewer_data, render_svg, render_html
from test_motion_preview import bound_job, SETUP


@pytest.fixture
def source():
    trace=plan_motion_preview(bound_job(True),SETUP,start_xy=(0,0))
    text=render_gcode_preview(trace)
    return trace,text


def test_viewer_uses_exact_readback(source):
    trace,text=source
    data=viewer_data(trace,text)
    parsed=read_gcode_preview(text)
    assert len(data["events"])==846
    assert data["moves"]==841
    assert [e["b"] for e in data["events"]]==[e.end for e in parsed.events]
    assert [e["a"] for e in data["events"]]==[e.start for e in parsed.events]
    assert data["bounds"]==[[-0.502,30.502],[-0.502,20.502],[-1.6,3]]
    assert len(data["stages"])==5


def test_svg_valid_xml_and_views(source):
    data=viewer_data(*source)
    svg=render_svg(data)
    root=ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "XY | Top view" in svg and "XZ | Side view" in svg
    assert "OFFLINE ONLY" in svg and "stroke-dasharray" in svg
    assert all(s["color"] in svg for s in data["stages"])


def test_html_embeds_actual_events_and_controls(source):
    data=viewer_data(*source)
    html=render_html(data)
    embedded=re.search(r'<script type="application/json" id="data">(.*?)</script>',html).group(1)
    parsed=json.loads(embedded)
    assert parsed==json.loads(json.dumps(data))
    assert all(f'id="{i}"' in html for i in ("step","prev","next","stage","rapid","canvas"))
    assert "https://" not in html
    assert "no machine connection" in html


def test_unwrapped_or_tampered_preview_rejected(source):
    trace,text=source
    with pytest.raises(ValueError):
        viewer_data(trace,text.replace(";@preview G21","G21",1))
    with pytest.raises(ValueError):
        viewer_data(trace,text.replace(";@preview G90",";@preview G91",1))


def test_name_cannot_inject_script(source):
    data=viewer_data(*source)
    data["name"]="</script><script>alert(1)</script>"
    html=render_html(data)
    assert "</script><script>alert(1)</script>" not in html
    assert "&lt;/script&gt;" in html
