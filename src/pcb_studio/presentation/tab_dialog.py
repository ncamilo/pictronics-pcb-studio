"""Modal graphical editor for full-height exterior holding tabs."""
from math import dist
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter,QPen,QColor,QPainterPath
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
                               QDialogButtonBox)
from pcb_studio.presentation.board_widget import BoardWidget
from pcb_studio.domain.pcb import outline_boards
from pcb_studio.presentation.viewport import Viewport
from pcb_studio.infrastructure.cam.geometry_job import assumed_stock
from pcb_studio.infrastructure.cam.tab_layout import snap_exterior,preset_anchors,preview_tabs


class TabCanvas(BoardWidget):
    clicked=Signal(object,bool)

    def mousePressEvent(self,event):
        if self.viewport and event.button() in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton):
            if QRectF(*self.plot_rect()).contains(event.position()):
                self.clicked.emit(self.world_at(event.position()),event.button()==Qt.MouseButton.RightButton)
            event.accept()
        else:
            super().mousePressEvent(event)

    def __init__(self):
        super().__init__()
        self.anchors=()
        self.cutout=None

    def paintEvent(self,event):
        super().paintEvent(event)
        if self.viewport is None:
            return
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setClipRect(QRectF(*self.plot_rect()))
        p.setBrush(Qt.BrushStyle.NoBrush)
        if self.cutout:
            for paths,color,width in ((self.cutout.exterior_paths,"#56e0b2",2),
                                      (self.cutout.tab_gaps,"#f1b66e",5)):
                p.setPen(QPen(QColor(color),width))
                for path in paths:
                    line=QPainterPath(self.screen_at(path[0]))
                    for xy in path[1:]:
                        line.lineTo(self.screen_at(xy))
                    p.drawPath(line)
        p.setPen(QPen(QColor("#f1b66e"),2))
        for i,xy in enumerate(self.anchors,1):
            pt=self.screen_at(xy)
            p.drawEllipse(pt,5,5)
            p.drawText(pt+QPointF(7,-8),str(i))
        p.end()


class TabDialog(QDialog):
    def __init__(self,project,anchors,width,cutter,stock_margin,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Place holding tabs — offline")
        self.resize(900,620)
        self.outline=project.outline
        self.width=width
        self.cutter=cutter
        self.stock_margin=stock_margin
        self.anchors=tuple(tuple(xy) for xy in anchors)
        layout=QVBoxLayout(self)
        note=QLabel(f"Full-height tabs | Width {width:g} mm | Cutter {cutter:g} mm | "
                    f"Nominal gap {width+cutter:g} mm | {len(outline_boards(self.outline))} boards. Presets apply per board. Left click near exterior to add; "
                    "right click near a numbered anchor to remove. Wheel zoom; middle drag to pan.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.canvas=TabCanvas()
        self.canvas.set_project(project)
        stock=assumed_stock(self.outline,stock_margin)
        xs,ys=zip(*stock.exterior)
        self.canvas.viewport=Viewport((min(xs),min(ys),max(xs),max(ys)))
        self.canvas.clicked.connect(self.edit_at)
        layout.addWidget(self.canvas,1)
        row=QHBoxLayout()
        for label,mode in (("2 left/right","lr"),("2 top/bottom","tb"),("4 sides","four")):
            button=QPushButton(label)
            button.clicked.connect(lambda checked=False,mode=mode:self.apply_preset(mode))
            row.addWidget(button)
        self.clear=QPushButton("Clear all")
        self.clear.clicked.connect(lambda:self.try_layout(()))
        row.addWidget(self.clear)
        fit=QPushButton("Fit to View")
        fit.clicked.connect(self.canvas.fit_view)
        row.addWidget(fit)
        layout.addLayout(row)
        self.status=QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.try_layout(self.anchors)

    def try_layout(self,anchors):
        try:
            result=preview_tabs(self.outline,anchors,self.width,self.cutter,self.stock_margin)
        except ValueError as exc:
            self.status.setText(f"Layout rejected: {exc}")
            self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.canvas.cutout is not None)
            return False
        self.anchors=tuple(anchors)
        self.canvas.anchors=self.anchors
        self.canvas.cutout=result
        self.canvas.update()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.status.setText(f"{len(self.anchors)} tabs | Green: cut centerline | Amber: actual gap"
                            + (" | No retention tabs" if not self.anchors else ""))
        return True

    def apply_preset(self,mode):
        return self.try_layout(preset_anchors(self.outline,mode))

    def edit_at(self,xy,remove=False):
        # A pixel-based radius makes selection consistent across zoom levels.
        tol=12/self.canvas.viewport.scale(self.canvas.plot_rect())
        if remove:
            if not self.anchors:
                return False
            i=min(range(len(self.anchors)),key=lambda i:dist(xy,self.anchors[i]))
            if dist(xy,self.anchors[i])>tol:
                self.status.setText("Click closer to a numbered tab")
                return False
            return self.try_layout(self.anchors[:i]+self.anchors[i+1:])
        try:
            anchor=snap_exterior(self.outline,xy,tol)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        return self.try_layout(self.anchors+(anchor,))
