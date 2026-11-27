"""Independent 12-board synthetic fixture; not the user's private design."""
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("gerbonara")
pytest.importorskip("shapely")
from pcb_studio.domain.pcb import PanelOutline
from test_desktop_preview import app,window
from test_gerbonara_adapter import rectangle_loop
from test_desktop_import import load
from test_desktop_cam import SETTINGS
from pcb_studio.infrastructure.cam.tab_layout import preset_anchors
from pcb_studio.domain.depth import DepthSetup
from pcb_studio.domain.tools import ProcessSettings
from pcb_studio.domain.work_frame import WorkFrame
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
import json


def test_panel_import_plan_export_and_persistence(window,app,tmp_path):
    copper=tmp_path/"panel_bottom.gbr"
    outline=tmp_path/"panel_outline.gbr"
    header="%FSLAX46Y46*%\n%MOMM*%\n%ADD10C,0.05*%\nD10*\n"
    points=[(col*14,row*10-20) for row in range(2) for col in range(6)]
    outline.write_text(header+"\n".join(rectangle_loop(x,y,10,6) for x,y in points)+"\nM02*\n")
    copper.write_text(header+"\n".join(f"X{(x+5)*1000000}Y{(y+3)*1000000}D03*" for x,y in points)+"\nM02*\n")
    assert window.import_files(name="Synthetic panel",bottom=str(copper),outline=str(outline)),window.message.text()
    assert isinstance(window.project.outline,PanelOutline)
    assert len(window.project.outline.boards)==12
    assert len(window.project.copper[0].polygons)==12
    assert window.outline_bounds()==pytest.approx((0,-20,80,-4))
    assert window.plan_cam.isEnabled()
    assert not window.save_nc.isEnabled()
    anchors=preset_anchors(window.project.outline,"four")
    assert len(anchors)==48
    assert window.generate_cam(**(SETTINGS|{"tab_anchors":anchors})),window.message.text()
    assert window.save_cam.isEnabled() and window.save_nc.isEnabled()
    assert len(window.cam_job.cutout.tab_gaps)==48
    assert len(window.cam_job.cutout.exterior_paths)==48
    assert window.cam_job.stages[0].feature_count==12
    assert "Tabs: 48" in window.tab_count.text()
    window.set_work_frame(WorkFrame((-3,-23)))
    folder=window.write_nc_previews(tmp_path,DepthSetup(1.6,3,0.1),(ProcessSettings(0.1,0.1,30,10000,100),ProcessSettings(1.6,0.8,30,10000,100)))
    assert folder is not None,window.message.text()
    assert len(list(folder.glob("*.preview.nc")))==2
    m=json.loads((folder/"manifest.json").read_text())
    assert m["work_frame"]["origin"]==[-3,-23]
    assert all(s["bounds_xy"][0]>=0 and s["bounds_xy"][1]>=0 for s in m["stages"])
    assert "CAM geometry" in window.detail.text()
    app.processEvents()
    assert not window.grab().isNull()
    path=tmp_path/"panel.pcbstudio.json"
    window.write_project(path)
    copper.unlink()
    outline.unlink()
    assert load(window)
    assert window.plan_cam.isEnabled()
    assert window.read_project(path),window.message.text()
    assert len(window.project.outline.boards)==12
    assert all(b.source=="panel_outline.gbr" for b in window.project.outline.boards)
    assert window.plan_cam.isEnabled()
    assert len(window.cam_job.cutout.tab_gaps)==48
    assert window.work_frame.origin==(-3,-23)


def test_pick_zero_and_presets(window,app):
    from pcb_studio.presentation.work_frame_dialog import WorkFrameDialog
    assert load(window)
    app.processEvents()
    d=WorkFrameDialog(window.outline_bounds(),None,window.work_frame)
    assert d.preset.currentData()=="board"
    d.preset.setCurrentIndex(d.preset.findData("center"))
    assert d.selection().origin==(15,10)
    d.close()
    window.pick_zero.click()
    pixel=window.board.screen_at((5,10)).toPoint()
    xy=window.board.world_at(pixel)
    QTest.mouseClick(window.board,Qt.MouseButton.LeftButton,pos=pixel)
    assert window.work_frame.origin==pytest.approx(xy)
    assert window.work_frame.to_work(xy)==pytest.approx((0,0))
    assert not window.pick_zero.isChecked()
    assert "0.000" in window.cursor.text()
