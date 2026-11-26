import pytest
pytest.importorskip("PySide6")
pytest.importorskip("gerbonara")
pytest.importorskip("shapely")
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from test_desktop_preview import app,window
from test_desktop_import import load


@pytest.fixture
def board(window,app):
    assert load(window),window.message.text()
    app.processEvents()
    return window.board


def test_wheel_anchor(board,app):
    p=QPointF(board.width()/3,board.height()/3)
    world=board.world_at(p)
    event=QWheelEvent(p,p,QPoint(),QPoint(0,120),Qt.MouseButton.NoButton,
                      Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
    app.sendEvent(board,event)
    assert board.viewport.zoom==pytest.approx(1.2)
    assert board.world_at(p)==pytest.approx(world)


def test_middle_drag_and_fit(board,window):
    p=QPoint(150,150)
    QTest.mousePress(board,Qt.MouseButton.MiddleButton,pos=p)
    QTest.mouseMove(board,p+QPoint(30,20))
    QTest.mouseRelease(board,Qt.MouseButton.MiddleButton,pos=p+QPoint(30,20))
    assert board.viewport.pan==pytest.approx((30,20))
    window.fit.click()
    assert board.viewport.pan==(0,0)
    assert board.viewport.zoom==1


def test_measure_and_grid(board,window,app):
    window.measure.setChecked(True)
    board.measure_at((5,10))
    board.measure_at((25,10))
    assert "20.000 mm" in window.measurement.text()
    window.grid.setChecked(False)
    assert not board.show_grid
    app.processEvents()
    assert not window.grab().isNull()
    window.measure.setChecked(False)
    assert board.measure_points==[]


def test_reimport_resets_navigation(board,window):
    board.viewport.translate(50,50)
    window.measure.setChecked(True)
    board.measure_at((5,10))
    assert load(window)
    assert board.viewport.pan==(0,0)
    assert board.measure_points==[]
    assert not window.measure.isChecked()
    window.load.click()
    assert window.inspect_bar.isHidden()
