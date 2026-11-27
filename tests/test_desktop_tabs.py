import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from pcb_studio.presentation.tab_dialog import TabDialog
from pcb_studio.presentation.cam_dialog import CamDialog
from pcb_studio.infrastructure.cam.tab_layout import snap_exterior,preview_tabs,preset_anchors
from test_desktop_preview import app,window
from test_desktop_import import load
from test_desktop_cam import SETTINGS


@pytest.fixture
def editor(window,app):
    assert load(window)
    d=TabDialog(window.project,(),2,1,3)
    d.show()
    app.processEvents()
    yield d
    d.close()


def test_snap_and_reject_distant(editor):
    assert snap_exterior(editor.outline,(15,0.1),0.2)==pytest.approx((15,0))
    with pytest.raises(ValueError):
        snap_exterior(editor.outline,(15,10),0.2)


@pytest.mark.parametrize("mode,count",[("lr",2),("tb",2),("four",4)])
def test_presets(editor,mode,count):
    assert editor.apply_preset(mode),editor.status.text()
    assert len(editor.anchors)==count
    assert editor.canvas.cutout.tab_gaps==preview_tabs(editor.outline,
            preset_anchors(editor.outline,mode),2,1,3).tab_gaps
    assert len(editor.canvas.cutout.exterior_paths)==count


def test_mouse_add_remove(editor,app):
    canvas=editor.canvas
    pos=canvas.screen_at((15,0)).toPoint()
    QTest.mouseClick(canvas,Qt.MouseButton.LeftButton,pos=pos)
    assert len(editor.anchors)==1
    assert editor.anchors[0]==pytest.approx((15,0),abs=0.1)
    QTest.mouseClick(canvas,Qt.MouseButton.RightButton,pos=pos)
    assert not editor.anchors
    app.processEvents()
    assert not editor.grab().isNull()


def test_rejected_changes_keep_last_valid(editor):
    assert editor.apply_preset("four")
    old=editor.anchors
    cut=editor.canvas.cutout
    assert not editor.try_layout(old+(old[0],))
    assert editor.anchors==old and editor.canvas.cutout is cut
    assert not editor.try_layout(((0,0),))
    assert editor.anchors==old


def test_selection_into_cam(window,editor,tmp_path):
    assert editor.apply_preset("four")
    dialog=CamDialog(window.project)
    dialog.anchors.setText("; ".join(f"{x!r},{y!r}" for x,y in editor.anchors))
    assert window.generate_cam(**dialog.selection()),window.message.text()
    assert window.cam_job.cutout.tab_gaps==editor.canvas.cutout.tab_gaps
    assert len(window.cam_geometry["tab_gaps"])==4
    assert not any(d["code"]=="no_external_tabs" for d in window.cam_geometry["diagnostics"])
    dialog.close()
