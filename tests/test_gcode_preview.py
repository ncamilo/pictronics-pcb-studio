"""Roundtrip actual CAM events through a strict comment-only G-code subset."""
import pytest
from pathlib import Path
pytest.importorskip("shapely")
pytest.importorskip("numpy")
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
from pcb_studio.infrastructure.cam.gcode_preview import render_gcode_preview
from pcb_studio.infrastructure.cam.gcode_readback import read_gcode_preview,compare_gcode_preview
from test_motion_preview import bound_job, SETUP, STOCK, TABS, LIB, ISO, DRILL, CUT


@pytest.fixture
def trace():
    return plan_motion_preview(bound_job(True),SETUP,start_xy=(0,0))


def test_complex_roundtrip(trace):
    text=render_gcode_preview(trace)
    assert all(line.startswith(";@preview ") for line in text.splitlines())
    result=compare_gcode_preview(trace,text)
    assert result.event_count==846 and result.stage_count==5
    assert result.movement_count==841
    assert result.max_coordinate_error_mm<=0.000000501
    assert not result.manufacturing_ready
    print(f"complex G-code readback: {result}")


@pytest.mark.parametrize("old,new",[
    (";@preview G21",";@preview G20"),
    (";@preview G90",";@preview G91"),
    (";@preview G94",";@preview G93"),
    (";@preview STAGE 0",";@preview STAGE 1"),
    (";@preview G1 Z-0.100000 F30.000000",";@preview G1 Z-0.100000 F0.000000"),
    (";@preview G1 Z-0.100000 F30.000000",";@preview G1 Z-0.100000 F31.000000"),
    (";@preview G1 Z-0.100000 F30.000000",";@preview G1 Z-0.200000 F30.000000"),
    (";@preview G0 Z3.000000",";@preview G0 Z2.000000"),
    (";@preview G21","G21"),
    (";@preview G21",";@preview M3"),
    (";@preview G21",";@preview G21 S10000"),
    (";@preview END OFFLINE PREVIEW",";@preview M30"),
])
def test_tampering_rejected(trace,old,new):
    text=render_gcode_preview(trace)
    assert old in text
    with pytest.raises(ValueError):
        compare_gcode_preview(trace,text.replace(old,new,1))


@pytest.mark.parametrize("mode",["delete","duplicate","extra","wrong_xy"])
def test_event_mutation_rejected(trace,mode):
    lines=render_gcode_preview(trace).splitlines()
    i=next(i for i,line in enumerate(lines) if line.startswith(";@preview G1 X"))
    if mode=="delete":
        del lines[i]
    elif mode=="duplicate":
        lines.insert(i,lines[i])
    elif mode=="extra":
        lines.insert(-1,";@preview G0 X0.000000 Y0.000000")
    else:
        words=lines[i].split()
        words[2]="X999.000000"
        lines[i]=" ".join(words)
    with pytest.raises(ValueError):
        compare_gcode_preview(trace,"\n".join(lines))


def test_actual_import_roundtrip():
    pytest.importorskip("gerbonara")
    from pcb_studio.application.import_project import import_project
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    from pcb_studio.infrastructure.cam.job_preview import plan_job_preview
    from pcb_studio.infrastructure.cam.tool_binding import bind_job_tools,isolation_tool_spec
    root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    p=import_project(GerbonaraImporter(),"synthetic",
                     copper_files=((root/"bottom.gbr","bottom"),),
                     drill_files=(root/"drills.drl",),outline_file=root/"outline.gbr")
    j=plan_job_preview(p,STOCK,isolation_tools=(isolation_tool_spec(LIB,ISO),),
                       target_width_mm=0.15,cutout_diameter_mm=1,tabs=TABS)
    t=plan_motion_preview(bind_job_tools(j,LIB,(ISO,DRILL,CUT)),SETUP,start_xy=(0,0))
    text=render_gcode_preview(t)
    result=compare_gcode_preview(t,text)
    assert result.event_count==1472 and result.stage_count==3
    assert len(read_gcode_preview(text).events)==len(t.events)
    print(f"imported G-code readback: {result}; lines={len(text.splitlines())}")
    lines=text.splitlines()
    i=lines.index(";@preview STAGE 1")
    k=lines.index(";@preview STAGE 2")
    print("DRILL PREVIEW BEGIN\n"+"\n".join(lines[i:k])+"\nDRILL PREVIEW END")
