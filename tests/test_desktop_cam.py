import json
from dataclasses import replace
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from PySide6.QtCore import Qt
from pcb_studio.presentation.cam_dialog import CamDialog
from test_desktop_preview import app,window
from test_desktop_import import load

SETTINGS=dict(side="bottom",diameter=0.15,target=0.15,passes=1,overlap=0.2,
              cutter=1,stock_margin=3,tab_anchors=((15,0),(30,10),(15,20),(0,10)),tab_width=2)


def test_plan_export_and_overlay(window,app,tmp_path):
    assert load(window)
    assert window.plan_cam.isEnabled() and not window.save_cam.isEnabled()
    assert window.generate_cam(**SETTINGS),window.message.text()
    assert window.save_cam.isEnabled()
    data=window.cam_geometry
    assert [s["operation"] for s in data["stages"]]==["isolation","drill","cutout_external"]
    assert data["stages"][1]["feature_count"]==2
    assert len(data["tab_gaps"])==4
    assert not data["manufacturing_ready"]
    assert window.board.cam is data
    app.processEvents()
    assert not window.grab().isNull()
    item=window.tree.topLevelItem(0).child(3)
    item.setCheckState(0,Qt.CheckState.Unchecked)
    assert ("cam",0) in window.board.hidden_layers
    p=tmp_path/"demo.cam.json"
    window.write_cam_json(p)
    assert json.loads(p.read_text())["format"]=="offline-cam-geometry"
    with pytest.raises(ValueError):
        window.write_cam_json(tmp_path/"bad.nc")


def test_dual_side_explicit_selection(window):
    assert load(window)
    project=window.project
    window.set_project(replace(project,copper=(replace(project.copper[0],side="top"),project.copper[0])))
    dialog=CamDialog(window.project)
    assert dialog.selection()["side"] is None
    assert not window.generate_cam(**(SETTINGS|{"side":None}))
    assert window.generate_cam(**SETTINGS),window.message.text()
    assert ("copper",0) in window.board.hidden_layers
    assert len(window.project.copper)==2
    assert window.cam_geometry["side"]=="bottom"
    dialog.close()


def test_failed_plan_preserves_preview_and_reimport_clears(window):
    assert load(window)
    assert window.generate_cam(**SETTINGS)
    old=window.cam_geometry
    assert not window.generate_cam(**(SETTINGS|{"stock_margin":0}))
    assert window.cam_geometry is old
    assert load(window)
    assert window.cam_geometry is None
    assert not window.save_cam.isEnabled()


def test_no_tabs_diagnostic(window):
    assert load(window)
    assert window.generate_cam(**(SETTINGS|{"tab_anchors":()}))
    assert any(d["code"]=="no_external_tabs" for d in window.cam_geometry["diagnostics"])
