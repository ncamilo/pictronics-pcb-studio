"""Read-only native Qt layer rendering in canonical XY."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BoardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.project = None
        self.hidden_layers = set()
        self.setMinimumSize(430, 380)

    def set_project(self, project):
        self.project = project
        self.hidden_layers.clear()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#182638"))
        project = self.project
        if project is None:
            return
        points = [xy for layer in project.copper for poly in layer.polygons for xy in poly.exterior]
        if project.outline:
            points.extend(project.outline.exterior)
        for layer in project.drills:
            for feature in (*layer.drills, *layer.slots):
                r = feature.diameter_mm / 2
                centers = (feature.center,) if hasattr(feature, "center") else (feature.start, feature.end)
                for x, y in centers:
                    points.extend(((x-r,y-r),(x+r,y+r)))
        if not points:
            return
        xs, ys = zip(*points)
        xmin,xmax,ymin,ymax = min(xs),max(xs),min(ys),max(ys)
        rect = QRectF(self.rect()).adjusted(28,48,-28,-38)
        scale = min(rect.width()/max(xmax-xmin,1e-9),rect.height()/max(ymax-ymin,1e-9))

        def point(xy):
            return QPointF(rect.center().x()+(xy[0]-(xmin+xmax)/2)*scale,
                           rect.center().y()-(xy[1]-(ymin+ymax)/2)*scale)

        def shape(rings):
            path=QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for ring in rings:
                path.moveTo(point(ring[0]))
                for xy in ring[1:]:
                    path.lineTo(point(xy))
                path.closeSubpath()
            return path

        p.setPen(QColor("#a8bacc"))
        p.drawText(QPointF(20,25),"XY / Imported geometry — canonical coordinates")
        if project.outline and ("outline",0) not in self.hidden_layers:
            outline=shape((project.outline.exterior,*project.outline.holes))
            p.fillPath(outline,QColor("#304c43"))
            p.setPen(QPen(QColor("#9ab7a5"),1.5))
            p.drawPath(outline)
        for i,layer in enumerate(project.copper):
            if ("copper",i) in self.hidden_layers:
                continue
            color=QColor("#dfb85d" if layer.side=="bottom" else "#df895c")
            color.setAlpha(210)
            for poly in layer.polygons:
                p.fillPath(shape((poly.exterior,*poly.holes)),color)
        for i,layer in enumerate(project.drills):
            if ("drill",i) in self.hidden_layers:
                continue
            p.setPen(QPen(QColor("#69b9ff"),1.2))
            p.setBrush(QColor("#182638"))
            for drill in layer.drills:
                r=drill.diameter_mm*scale/2
                p.drawEllipse(point(drill.center),r,r)
            for slot in layer.slots:
                pen=QPen(QColor("#69b9ff"),slot.diameter_mm*scale)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(pen)
                p.drawLine(point(slot.start),point(slot.end))
        p.setPen(QColor("#a8bacc"))
        p.drawText(QPointF(20,self.height()-14),
                   f"Input extent: {xmax-xmin:.3f} x {ymax-ymin:.3f} mm | No mirroring")
