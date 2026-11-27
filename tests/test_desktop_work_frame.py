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


@pytest.mark.parametrize("mirror",["none","x","y"])
def test_view_and_json_same_as_nc(window,tmp_path,mirror):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    frame=WorkFrame((30,20),mirror)
    window.set_work_frame(frame)
    board=window.board
    assert board.work_at(board.screen_at(frame.origin))==pytest.approx((0,0),abs=1e-10)
    p=(5,10)
    assert board.work_at(board.screen_at(p))==pytest.approx(frame.to_work(p))
    assert board.world_at(board.screen_at(p))==pytest.approx(p)
    # Display axes are fixed in work coordinates even when mirrored.
    assert board.screen_at(frame.to_board((1,0))).x()>board.screen_at(frame.origin).x()
    assert board.screen_at(frame.to_board((0,1))).y()<board.screen_at(frame.origin).y()
    dest=tmp_path/"work.cam.json"
    window.write_cam_json(dest)
    data=json.loads(dest.read_text())
    assert data["schema_version"]==2
    assert data["coordinate_system"]=="work XY"
    assert data["work_frame"]=={"origin":[30,20],"mirror":mirror}
    for before,after in zip(window.cam_geometry["stages"],data["stages"]):
        for a,b in zip(before["paths"],after["paths"]):
            assert all(q==pytest.approx(frame.to_work(p)) for p,q in zip(a,b))
    assert data["stock_bounds"]==pytest.approx(frame.bounds(window.cam_geometry["stock_bounds"]))
    folder=window.write_nc_previews(tmp_path,SETUP,PARAMS)
    assert folder is not None,window.message.text()
    files=sorted(folder.glob("*.nc"))
    for stage,path in zip(data["stages"],files):
        moves=xy_words(path.read_text())
        for line in stage["paths"]:
            assert any(q==pytest.approx(line[0],abs=1e-6) for q in moves)


def test_snap_exact_corner_and_cancel(window,app):
    from PySide6.QtCore import Qt,QPoint
    from PySide6.QtTest import QTest
    assert load(window)
    app.processEvents()
    window.pick_zero.click()
    pixel=window.board.screen_at((30,20)).toPoint()+QPoint(-3,3)
    QTest.mouseClick(window.board,Qt.MouseButton.LeftButton,pos=pixel)
    assert window.work_frame.origin==(30,20)
    assert not window.pick_zero.isChecked()
    assert window.board.work_at(window.board.screen_at((30,20)))==pytest.approx((0,0))
    old=window.work_frame
    window.pick_zero.click()
    QTest.mouseClick(window.board,Qt.MouseButton.RightButton,pos=pixel)
    assert not window.pick_zero.isChecked()
    assert window.work_frame==old


def test_cached_paths_survive_view_changes(window,app):
    from PySide6.QtCore import QPointF
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    b=window.board
    cached=(b._outline_paths,b._copper_paths,b._cam_paths)
    for mirror in ("none","x","y"):
        window.set_work_frame(WorkFrame((30,20),mirror))
        b.viewport.zoom_at((100,120),2,b.plot_rect())
        b.viewport.translate(25,-15)
        for xy in ((0,0),(5,10),(30,20)):
            p=b.source_transform().map(QPointF(*xy))
            expected=b.screen_at(xy)
            assert (p.x(),p.y())==pytest.approx((expected.x(),expected.y()))
        app.processEvents()
        assert not b.grab().isNull()
        assert all(a is c for a,c in zip(cached,(b._outline_paths,b._copper_paths,b._cam_paths)))
    assert load(window)
    assert b._copper_paths is not cached[1]
    assert b._cam_paths==()
