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


def test_panel_import_persistence_and_cam_gate(window,app,tmp_path):
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
    assert not window.plan_cam.isEnabled()
    assert not window.save_nc.isEnabled()
    assert not window.generate_cam(**SETTINGS)
    assert "Panel CAM" in window.message.text()
    assert "12 boards" in window.detail.text()
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
    assert not window.plan_cam.isEnabled()
