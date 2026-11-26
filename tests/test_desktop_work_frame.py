import json
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from pcb_studio.domain.work_frame import WorkFrame
from pcb_studio.infrastructure.cam.nc_stage_preview import build_stage_nc
from pcb_studio.presentation.work_frame_dialog import WorkFrameDialog
from test_desktop_preview import app,window
from test_desktop_import import load
from test_desktop_cam import SETTINGS
from test_nc_stage_preview import SETUP,PARAMS


def xy_words(text):
    return [tuple(float(v[1:]) for v in line.split()[1:3])
            for line in text.splitlines() if line.startswith(("G0 X","G1 X"))]


@pytest.mark.parametrize("mirror",["none","x","y"])
def test_all_files_transform(window,mirror):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    original=window.cam_job
    frame=WorkFrame((30,20),mirror)
    a=build_stage_nc(original,SETUP,PARAMS,start_xy=(-3,-3))
    b=build_stage_nc(original,SETUP,PARAMS,start_xy=(-3,-3),frame=frame)
    for name in a:
        if name.endswith(".nc"):
            assert len(xy_words(a[name]))==len(xy_words(b[name]))
            for before,after in zip(xy_words(a[name]),xy_words(b[name])):
                assert after==pytest.approx(frame.to_work(before),abs=1.1e-6)
            assert [l for l in a[name].splitlines() if l.startswith(("G0 Z","G1 Z"))]==[
                    l for l in b[name].splitlines() if l.startswith(("G0 Z","G1 Z"))]
    m=json.loads(b["manifest.json"])
    assert m["work_frame"]=={"origin":[30,20],"mirror":mirror}
    assert m["cut_direction_reversed"]==(mirror!="none")
    assert window.cam_job is original


def test_dialog_and_gui_export(window,tmp_path,app):
    assert load(window)
    assert window.work_frame.origin==(0,0)
    dialog=WorkFrameDialog(window.outline_bounds(),None,window.work_frame)
    dialog.preset.setCurrentIndex(dialog.preset.findData("board"))
    dialog.mirror.setCurrentIndex(dialog.mirror.findData("x"))
    frame=dialog.selection()
    assert frame==WorkFrame((30,0),"x")
    window.set_work_frame(frame)
    assert window.board.work_frame==frame
    assert window.generate_cam(**SETTINGS)
    folder=window.write_nc_previews(tmp_path,SETUP,PARAMS)
    assert folder is not None,window.message.text()
    assert json.loads((folder/"manifest.json").read_text())["work_frame"]["mirror"]=="x"
    app.processEvents()
    assert not window.grab().isNull()
    assert load(window)
    assert window.work_frame==WorkFrame()
    dialog.close()
