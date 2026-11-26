"""Headless native Qt smoke and interaction tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
import pytest
pytest.importorskip("PySide6")
pytest.importorskip("shapely")
pytest.importorskip("numpy")
pytest.importorskip("gerbonara")
from PySide6.QtWidgets import QApplication
from pcb_studio.application.machine_service import MachineService
from pcb_studio.infrastructure.cnc.simulator import SimulatedMachine
from pcb_studio.presentation.window import create_window


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    w=create_window(MachineService(SimulatedMachine()))
    w.show()
    w.load.click()
    app.processEvents()
    yield w
    w.close()


def test_loaded_actual_demo(window):
    assert window.data is not None
    assert len(window.data["events"])==1472
    assert window.slider.maximum()==1472
    assert window.tree.topLevelItem(0).childCount()==3
    assert "Not manufacturing-ready" in window.message.text()


def test_navigation(window):
    window.slider.setValue(0)
    assert not window.previous.isEnabled()
    assert window.next.isEnabled()
    window.next.click()
    assert window.canvas.step==1
    assert "1/1472" in window.detail.text()
    window.previous.click()
    assert window.canvas.step==0


def test_filters(window):
    window.stage.setCurrentIndex(2)
    assert window.canvas.stage_filter==1
    window.rapid.setChecked(False)
    assert not window.canvas.show_rapid


def test_render_capture(window,app):
    app.processEvents()
    image=window.grab()
    assert not image.isNull() and image.width()>=1000


def test_failed_load_keeps_preview(window):
    old=window.data
    def fail():
        raise ValueError("fixture missing")
    window.demo_loader=fail
    window.load.click()
    assert window.data is old
    assert "fixture missing" in window.message.text()
