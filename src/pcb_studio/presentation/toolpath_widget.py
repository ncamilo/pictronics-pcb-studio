"""Native Qt rendering of offline readback centerlines."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class ToolpathWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = None
        self.step = 0
        self.stage_filter = None
        self.show_rapid = True
        self.setMinimumSize(430, 380)

    def set_data(self, data):
        self.data = data
        self.step = len(data["events"])
        self.stage_filter = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#101a27"))
        if not self.data:
            p.setPen(QColor("#a8bacc"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Load the synthetic board demo")
            return
        h = self.height()
        self._view(p, (0, 1), QRectF(18, 32, self.width()-36, h*0.60-42), "XY / Top view")
        self._view(p, (0, 2), QRectF(18, h*0.60+28, self.width()-36, h*0.40-46), "XZ / Side view")

    def _view(self, painter, axes, box, title):
        d = self.data
        painter.fillRect(box, QColor("#182638"))
        painter.setPen(QColor("#a8bacc"))
        painter.drawText(QPointF(box.left(), box.top()-9), title)
        plot = box.adjusted(18, 18, -18, -18)
        a, b = [d["bounds"][i] for i in axes]
        scale = min(plot.width()/max(a[1]-a[0], 1e-9),
                    plot.height()/max(b[1]-b[0], 1e-9))

        def point(v):
            return QPointF(plot.center().x()+(v[axes[0]]-(a[0]+a[1])/2)*scale,
                           plot.center().y()-(v[axes[1]]-(b[0]+b[1])/2)*scale)

        painter.save()
        painter.setClipRect(box)
        # Batch segments per kind and stage. No bridges between independent moves.
        paths, marks = {}, []
        for e in d["events"][:self.step]:
            kind, stage = e["kind"], e["stage"]
            if kind=="tool_setup" or (self.stage_filter is not None and stage!=self.stage_filter):
                continue
            if kind=="rapid_xy" and not self.show_rapid:
                continue
            start, end = point(e["a"]), point(e["b"])
            if axes==(0,1) and kind in ("plunge","retract"):
                if kind=="plunge":
                    marks.append((stage,end))
                continue
            if start==end:
                continue
            path=paths.setdefault((kind,stage),QPainterPath())
            path.moveTo(start)
            path.lineTo(end)
        for (kind,stage),path in sorted(paths.items(),key=lambda item:item[0][0]!="rapid_xy"):
            pen=QPen(QColor("#8092aa" if kind=="rapid_xy" else d["stages"][stage]["color"]))
            pen.setWidthF(1.5)
            if kind=="rapid_xy":
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawPath(path)
        for stage,pt in marks:
            painter.setPen(QPen(QColor(d["stages"][stage]["color"]),1.5))
            painter.drawEllipse(pt,3,3)
        current=d["events"][self.step-1]["b"] if self.step else d["initial"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(point(current),4,4)
        painter.restore()
