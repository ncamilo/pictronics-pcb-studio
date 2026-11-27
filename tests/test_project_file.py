import json
import shutil
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from shapely.geometry import LineString
from pcb_studio.domain.work_frame import WorkFrame
from pcb_studio.presentation.nc_dialog import NcDialog
from test_desktop_preview import app,window
from test_desktop_import import load,ROOT
from test_desktop_cam import SETTINGS
from test_nc_stage_preview import SETUP,PARAMS


def test_portable_project_roundtrip(window,tmp_path):
    inputs=tmp_path/"originals"
    shutil.copytree(ROOT,inputs)
    assert window.import_files(name="Portable PCB",bottom=str(inputs/"bottom.gbr"),
                               outline=str(inputs/"outline.gbr"),drills=(str(inputs/"drills.drl"),))
    assert window.generate_cam(**SETTINGS),window.message.text()
    frame=WorkFrame((33,-3),"x")
    window.set_work_frame(frame)
    assert window.write_nc_previews(tmp_path,SETUP,PARAMS)
    before=window.cam_geometry
    path=tmp_path/"saved.pcbstudio.json"
    window.write_project(path)
    shutil.rmtree(inputs)
    assert load(window)
    assert window.read_project(path),window.message.text()
    assert window.project.name=="Portable PCB"
    assert window.work_frame==frame
    assert window.cam_geometry==before
    assert window.nc_settings==(SETUP,PARAMS)
    assert window.save_nc.isEnabled()
    assert "Tabs: 4" in window.tab_count.text()
    dialog=NcDialog(window.cam_job,saved=window.nc_settings)
    assert dialog.selection()==(SETUP,PARAMS)
    dialog.close()


def test_unplanned_project(window,tmp_path):
    assert load(window)
    path=tmp_path/"unplanned.pcbstudio.json"
    window.write_project(path)
    assert window.generate_cam(**SETTINGS)
    assert window.read_project(path)
    assert window.cam_job is None and window.nc_settings is None
    assert not window.save_nc.isEnabled()


@pytest.mark.parametrize("corruption",["hash","version","tabs"])
def test_bad_project_retains_current(window,tmp_path,corruption):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    path=tmp_path/"bad.pcbstudio.json"
    window.write_project(path)
    data=json.loads(path.read_text())
    if corruption=="hash":
        data["sources"][0]["sha256"]="0"*64
    elif corruption=="version":
        data["schema_version"]=999
    else:
        data["cam"]["tab_anchors"]=[[0,0]]
    path.write_text(json.dumps(data))
    old=window.project
    old_cam=window.cam_job
    assert not window.read_project(path)
    assert window.project is old and window.cam_job is old_cam
    assert window.save_nc.isEnabled()


def test_actual_nc_preserves_four_gaps_at_both_depths(window,tmp_path):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    frame=WorkFrame((33,-3),"x")
    window.set_work_frame(frame)
    folder=window.write_nc_previews(tmp_path,SETUP,PARAMS)
    assert folder is not None,window.message.text()
    file=next(folder.glob("*cutout_external*.nc"))
    xy=None
    z=3
    cuts={}
    for line in file.read_text().splitlines():
        if line.startswith(("G0 Z","G1 Z")):
            z=float(line.split()[1][1:])
        elif line.startswith(("G0 X","G1 X")):
            end=tuple(float(v[1:]) for v in line.split()[1:3])
            if line.startswith("G1 X"):
                assert z<0 and xy is not None
                cuts.setdefault(z,[]).append(LineString([xy,end]))
            xy=end
    assert set(cuts)=={-0.8,-1.6}
    for gap in window.cam_job.cutout.tab_gaps:
        center=LineString([frame.to_work(p) for p in gap]).interpolate(0.5,normalized=True)
        for segments in cuts.values():
            assert min(s.distance(center) for s in segments)>=1.5-1e-6
    assert "Tabs: 4" in window.tab_count.text()
    assert window.generate_cam(**(SETTINGS|{"tab_anchors":()}))
    assert "Tabs: 0" in window.tab_count.text()
    assert window.nc_settings is None
