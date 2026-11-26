"""Read-only native Qt layer rendering in canonical XY."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from pcb_studio.domain.work_frame import WorkFrame
from pcb_studio.presentation.viewport import Viewport, grid_values, measure


class BoardWidget(QWidget):
    cursor_changed = Signal(str)
    measurement_changed = Signal(str)
    def __init__(self):
        super().__init__()
        self.project = None
        self.cam = None
        self.work_frame = WorkFrame()
        self.hidden_layers = set()
        self.viewport = None
        self.show_grid = True
        self.measuring = False
        self.measure_points = []
        self._drag = None
        self.setMouseTracking(True)
        self.setMinimumSize(430, 380)

    def set_project(self, project):
        self.project = project
        self.cam = None
        self.hidden_layers.clear()
        self.measure_points.clear()
        self.measuring=False
        self._drag=None
        self.viewport=self._build_viewport(project)
        self.cursor_changed.emit("Cursor: —")
        self.measurement_changed.emit("Measurement: —")
        self.update()

    def set_work_frame(self,frame):
        self.work_frame=frame
        self.update()

    def cursor_label(self,pixel):
        xy=self.world_at(pixel)
        return "Work X %.3f  Y %.3f mm" % self.work_frame.to_work(xy)

    def set_cam(self,data):
        self.cam=data
        self.hidden_layers={key for key in self.hidden_layers if key[0]!='cam'}
        self.viewport=Viewport(tuple(data['stock_bounds']))
        self.update()

    @staticmethod
    def _build_viewport(project):
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
        return Viewport((xmin,ymin,xmax,ymax))

    def plot_rect(self):
        r=QRectF(self.rect()).adjusted(28,48,-28,-38)
        return (r.x(),r.y(),r.width(),r.height())

    def world_at(self,pixel):
        return self.viewport.world((pixel.x(),pixel.y()),self.plot_rect())

    def screen_at(self,xy):
        return QPointF(*self.viewport.screen(xy,self.plot_rect()))

    def fit_view(self):
        if self.viewport:
            self.viewport.fit()
            self.update()

    def set_grid(self,checked):
        self.show_grid=checked
        self.update()

    def set_measure(self,checked):
        self.measuring=checked
        self.measure_points.clear()
        self.measurement_changed.emit("Select two XY points" if checked else "Measurement: —")
        self.update()

    def measure_at(self,xy):
        if not self.measuring:
            return
        if len(self.measure_points)==2:
            self.measure_points.clear()
        self.measure_points.append(xy)
        if len(self.measure_points)==2:
            dx,dy,d=measure(*self.measure_points)
            self.measurement_changed.emit(f"Distance {d:.3f} mm | dX {dx:.3f} | dY {dy:.3f}")
        else:
            self.measurement_changed.emit("Select second point")
        self.update()

    def wheelEvent(self,event):
        if self.viewport and event.angleDelta().y():
            pixel=event.position()
            factor=1.2**max(-10,min(10,event.angleDelta().y()/120))
            self.viewport.zoom_at((pixel.x(),pixel.y()),factor,self.plot_rect())
            self.cursor_changed.emit(self.cursor_label(pixel))
            self.update()
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self,event):
        if self.viewport and event.button()==Qt.MouseButton.MiddleButton:
            self._drag=event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif self.viewport and self.measuring and event.button()==Qt.MouseButton.LeftButton:
            self.measure_at(self.world_at(event.position()))
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self,event):
        if not self.viewport:
            return
        if self._drag is not None:
            delta=event.position()-self._drag
            self.viewport.translate(delta.x(),delta.y())
            self._drag=event.position()
            self.update()
        self.cursor_changed.emit(self.cursor_label(event.position()))

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self._drag=None
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self,event):
        self.cursor_changed.emit("Cursor: —")
        super().leaveEvent(event)


    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#182638"))
        project = self.project
        if project is None:
            return
        if not self.viewport:
            return
        xmin,ymin,xmax,ymax=self.viewport.bounds
        scale=self.viewport.scale(self.plot_rect())
        point=self.screen_at
        p.save()
        plot=QRectF(*self.plot_rect())
        p.setClipRect(plot)
        if self.show_grid:
            step=self.viewport.grid_step(self.plot_rect())
            lo=self.world_at(plot.bottomLeft())
            hi=self.world_at(plot.topRight())
            p.setPen(QPen(QColor("#34475b"),0.8))
            for x in grid_values(lo[0],hi[0],step):
                p.drawLine(point((x,lo[1])),point((x,hi[1])))
            for y in grid_values(lo[1],hi[1],step):
                p.drawLine(point((lo[0],y)),point((hi[0],y)))
            p.setPen(QPen(QColor("#6b8198"),1.2))
            if lo[0]<=0<=hi[0]:
                p.drawLine(point((0,lo[1])),point((0,hi[1])))
            if lo[1]<=0<=hi[1]:
                p.drawLine(point((lo[0],0)),point((hi[0],0)))

        def shape(rings):
            path=QPainterPath()
            path.setFillRule(Qt.FillRule.OddEvenFill)
            for ring in rings:
                path.moveTo(point(ring[0]))
                for xy in ring[1:]:
                    path.lineTo(point(xy))
                path.closeSubpath()
            return path

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
        if self.cam:
            colors={"isolation":"#56e0b2","drill":"#69b9ff","mill_slot":"#c69bff",
                    "cutout_internal":"#f1b66e","cutout_external":"#f1b66e"}
            p.setBrush(Qt.BrushStyle.NoBrush)
            for i,stage in enumerate(self.cam["stages"]):
                if ("cam",i) in self.hidden_layers:
                    continue
                p.setPen(QPen(QColor(colors[stage["operation"]]),1.6))
                paths=QPainterPath()
                for path in stage["paths"]:
                    if len(path)==1:
                        paths.addEllipse(point(path[0]),4,4)
                    else:
                        paths.moveTo(point(path[0]))
                        for xy in path[1:]:
                            paths.lineTo(point(xy))
                p.drawPath(paths)
        origin=point(self.work_frame.origin)
        sx,sy=self.work_frame.signs
        p.setPen(QPen(QColor("#56e0b2"),2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(origin,5,5)
        p.drawLine(origin,origin+QPointF(30*sx,0))
        p.drawLine(origin,origin+QPointF(0,-30*sy))
        p.drawText(origin+QPointF(6,-8),"X0 Y0")
        p.drawText(origin+QPointF(34*sx,-3),"X+")
        p.drawText(origin+QPointF(4,-34*sy),"Y+")
        p.setPen(QPen(QColor("#80d8ff"),1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for xy in self.measure_points:
            p.drawEllipse(point(xy),4,4)
        if len(self.measure_points)==2:
            a,b=self.measure_points
            p.drawLine(point(a),point(b))
            dx,dy,d=measure(a,b)
            p.drawText((point(a)+point(b))/2+QPointF(5,-8),f"{d:.3f} mm")
        p.restore()
        p.setPen(QColor("#a8bacc"))
        p.drawText(QPointF(20,25),"XY / CAM centerlines — source view, work axes shown" if self.cam else "XY / Imported geometry — source view, work axes shown")
        grid=f" | Grid {self.viewport.grid_step(self.plot_rect()):g} mm" if self.show_grid else ""
        p.drawText(QPointF(20,self.height()-14),
                   f"View extent: {xmax-xmin:.3f} x {ymax-ymin:.3f} mm{grid} | Zoom {self.viewport.zoom:.2f}x")
