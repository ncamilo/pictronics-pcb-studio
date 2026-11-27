import json
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from pcb_studio.domain.depth import DepthSetup
from pcb_studio.domain.tools import ProcessSettings
from pcb_studio.infrastructure.cam.nc_stage_preview import build_stage_nc, verify_stage_nc
from pcb_studio.presentation.nc_dialog import NcDialog
from test_desktop_preview import app,window
from test_desktop_import import load
from test_desktop_cam import SETTINGS

SETUP=DepthSetup(1.6,3,0.1)
PARAMS=(ProcessSettings(0.1,0.1,30,10000,100),
        ProcessSettings(1.6,0.8,30,10000),
        ProcessSettings(1.6,0.8,30,10000,80))


def test_nc_export_per_stage(window,tmp_path):
    assert load(window)
    assert not window.save_nc.isEnabled()
    assert window.generate_cam(**SETTINGS)
    assert window.save_nc.isEnabled()
    folder=window.write_nc_previews(tmp_path,SETUP,PARAMS)
    assert folder is not None,window.message.text()
    files=sorted(folder.glob("*.preview.nc"))
    assert len(files)==3
    for file in files:
        lines=file.read_text().splitlines()
        assert lines[1:4]==["G21","G90","G94"]
        assert lines[4]=="G0 Z3.000000"
        assert lines[5].startswith("G0 X")
        assert lines[-2]=="G0 Z3.000000"
        assert not any(line.startswith(("M","S","T")) for line in lines)
    manifest=json.loads((folder/"manifest.json").read_text())
    assert not manifest["manufacturing_ready"]
    assert manifest["virtual_tools"]
    assert [s["operation"] for s in manifest["stages"]]==["isolation","drill","cutout_external"]
    assert sum(s["collapsed_moves"] for s in manifest["stages"])==0
    assert "G1 Z-1.600000 F30.000000" in files[1].read_text()
    assert window.write_nc_previews(tmp_path,SETUP,PARAMS)!=folder


def test_inconsistent_depth_no_files(window,tmp_path):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    assert window.write_nc_previews(tmp_path,DepthSetup(2,3,0.1),PARAMS) is None
    assert not list(tmp_path.iterdir())


def test_dialog_and_reimport(window):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    dialog=NcDialog(window.cam_job)
    setup,params=dialog.selection()
    assert setup==SETUP
    assert params[1].feed_xy_mm_min is None
    assert params[0].depth_mm==0.1
    dialog.close()
    assert load(window)
    assert window.cam_job is None
    assert not window.save_nc.isEnabled()


def test_reject_modified_nc(window):
    from pcb_studio.domain.tools import CuttingTool,ToolLibrary
    from pcb_studio.infrastructure.cam.tool_binding import ToolSelection,bind_job_tools
    from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    job=window.cam_job
    start=(-3,-3)
    files=build_stage_nc(job,SETUP,PARAMS,start_xy=start)
    nc=next(v for k,v in files.items() if "_01_" in k)
    tools=tuple(CuttingTool(str(i),"virtual","drill" if s.operation=="drill" else "end_mill",
                            s.diameter_mm,p.depth_mm) for i,(s,p) in enumerate(zip(job.stages,PARAMS)))
    trace=plan_motion_preview(bind_job_tools(job,ToolLibrary(tools),tuple(
          ToolSelection(t.tool_id,p) for t,p in zip(tools,PARAMS))),SETUP,start_xy=start)
    events=[e for e in trace.events if e.stage_index==0 and e.kind!="tool_setup"]
    if events[0].kind=="rapid_xy":
        events=events[1:]
    assert verify_stage_nc(nc,events)["movements"]==len(events)
    for bad in (nc.replace("G90","G91",1),nc.replace("G0 Z3.000000","G0 Z2.000000",1),
                nc.replace("F30.000000","F31.000000",1),nc.replace("G21","M3",1)):
        with pytest.raises(ValueError):
            verify_stage_nc(bad,events)
