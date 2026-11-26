"""Desktop import using actual synthetic Gerber and Excellon files."""
from pathlib import Path
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("gerbonara")
from PySide6.QtCore import Qt
from pcb_studio.presentation.import_dialog import ImportDialog
from test_desktop_preview import app, window

ROOT=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"


def load(w,**kwargs):
    settings=dict(name="Imported fixture",bottom=str(ROOT/"bottom.gbr"),
                  drills=(str(ROOT/"drills.drl"),),outline=str(ROOT/"outline.gbr"))
    settings.update(kwargs)
    return w.import_files(**settings)


def test_import_layers(window,app):
    assert load(window),window.message.text()
    assert window.data is None
    assert window.project.copper[0].side=="bottom"
    assert len(window.project.drills[0].drills)==2
    assert window.project.outline is not None
    assert window.views.currentWidget() is window.board
    assert window.tree.topLevelItem(0).childCount()==3
    assert not window.slider.isEnabled()
    app.processEvents()
    assert not window.grab().isNull()


def test_layer_visibility(window):
    assert load(window)
    item=window.tree.topLevelItem(0).child(0)
    item.setCheckState(0,Qt.CheckState.Unchecked)
    assert ("copper",0) in window.board.hidden_layers
    item.setCheckState(0,Qt.CheckState.Checked)
    assert not window.board.hidden_layers


def test_failed_import_keeps_previous(window):
    assert load(window)
    old=window.project
    assert not load(window,bottom="missing.gbr")
    assert window.project is old
    assert window.views.currentWidget() is window.board
    assert "Import failed" in window.message.text()


def test_duplicate_file_roles_rejected(window):
    old=window.data
    assert not load(window,top=str(ROOT/"bottom.gbr"))
    assert window.data is old
    assert "more than once" in window.message.text()


def test_optional_outline_and_drills(window):
    assert load(window,outline="",drills=())
    assert window.project.outline is None
    assert not window.project.drills
    assert "Outline not supplied" in window.diagnostics.text()


def test_switch_back_to_cam_demo(window):
    assert load(window)
    window.load.click()
    assert window.project is None
    assert window.views.currentWidget() is window.canvas
    assert window.slider.maximum()==1472
    assert window.slider.isEnabled()


def test_dialog_roles(app):
    dialog=ImportDialog()
    dialog.name.setText("Test")
    dialog.bottom.setText(str(ROOT/"bottom.gbr"))
    dialog.drills.addItem(str(ROOT/"drills.drl"))
    assert dialog.selection()["bottom"].endswith("bottom.gbr")
    assert dialog.selection()["top"]==""
    assert len(dialog.selection()["drills"])==1
    dialog.close()
