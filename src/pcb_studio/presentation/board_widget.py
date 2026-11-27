"""Render immutable source geometry in a shared work XY frame."""
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QWidget
from pcb_studio.domain.work_frame import WorkFrame, reference_points, snap_reference
from pcb_studio.domain.pcb import outline_boards
from pcb_studio.presentation.viewport import Viewport, grid_values, measure


class BoardWidget(QWidget):
    cursor_changed = Signal(str)
    origin_picked = Signal(object)
    origin_cancelled = Signal()
    measurement_changed = Signal(str)
    def __init__(self):
        super().__init__()
        self.project = None
        self.cam = None
        self._outline_paths = ()
        self._copper_paths = ()
        self._cam_paths = ()
        self.work_frame = WorkFrame()
        self.hidden_layers = set()
        self.viewport = None
        self.source_bounds = None
        self.snap_preview = None
        self.show_grid = True
        self.measuring = False
        self.picking_origin = False
        self.measure_points = []
        self._drag = None
        self.setMouseTracking(True)
        self.setMinimumSize(430, 380)

    def set_project(self, project):
        self.project = project
        self.cam = None
        self._outline_paths = tuple(self._polygon_path((b.exterior,*b.holes))
                                    for b in outline_boards(project.outline))
        self._copper_paths = tuple(tuple(self._polygon_path((p.exterior,*p.holes))
                                         for p in layer.polygons) for layer in project.copper)
        self._cam_paths = ()
        self.hidden_layers.clear()
        self.measure_points.clear()
        self.measuring=False
        self.picking_origin=False
        self.unsetCursor()
        self._drag=None
        self.work_frame=WorkFrame()
        self.snap_preview=None
        source=self._build_viewport(project)
        self.source_bounds=source.bounds if source else None
        self.reframe()
        self.cursor_changed.emit("Cursor: —")
        self.measurement_changed.emit("Measurement: —")
        self.update()

    def set_work_frame(self,frame):
        self.work_frame=frame
        self.snap_preview=None
        self.reframe()
        if len(self.measure_points)==2:
            self.report_measurement()
        self.cursor_changed.emit("Work X —  Y —")
        self.update()

    def reframe(self):
        if self.source_bounds is None:
            self.viewport=None
            return
        a,b,c,d=self.work_frame.bounds(self.source_bounds)
        # Keep work zero visible on Fit, even outside the material.
        a,b,c,d=min(a,0),min(b,0),max(c,0),max(d,0)
        pad=max(c-a,d-b,1)*0.06
        self.viewport=Viewport((a-pad,b-pad,c+pad,d+pad))

    def set_pick_origin(self,checked):
        self.picking_origin=checked
        self.snap_preview=None
        self.update()
        if checked:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.unsetCursor()

    def cursor_label(self,pixel):
        return "Work X %.3f  Y %.3f mm" % self.work_at(pixel)

    def work_at(self,pixel):
        return self.viewport.world((pixel.x(),pixel.y()),self.plot_rect())

    def origin_candidate(self,pixel,free=False):
        xy=self.world_at(pixel)
        if free:
            return xy
        candidates=[]
        for board in outline_boards(self.project.outline):
            xs,ys=zip(*board.exterior)
            candidates.extend(reference_points((min(xs),min(ys),max(xs),max(ys))))
        boards=outline_boards(self.project.outline)
        if boards:
            xs,ys=zip(*(xy for board in boards for xy in board.exterior))
            candidates.extend(reference_points((min(xs),min(ys),max(xs),max(ys))))
        if self.cam:
            candidates.extend(reference_points(self.cam["stock_bounds"]))
        # Object references have priority, as in FlatCAM; free click otherwise.
        return snap_reference(xy,candidates,10/self.viewport.scale(self.plot_rect()))

    def set_cam(self,data):
        self.cam=data
        self._cam_paths=tuple(self._stage_path(stage) for stage in data['stages'])
        self.hidden_layers={key for key in self.hidden_layers if key[0]!='cam'}
        self.source_bounds=tuple(data['stock_bounds'])
        self.reframe()
        self.update()

    @staticmethod
    def _build_viewport(project):
        points = [xy for layer in project.copper for poly in layer.polygons for xy in poly.exterior]
        for board in outline_boards(project.outline):
            points.extend(board.exterior)
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
        return self.work_frame.to_board(self.work_at(pixel))

    def screen_at(self,xy):
        return QPointF(*self.viewport.screen(self.work_frame.to_work(xy),self.plot_rect()))

    @staticmethod
    def _polygon_path(rings):
        path=QPainterPath()
        path.setFillRule(Qt.FillRule.OddEvenFill)
        for ring in rings:
            path.moveTo(*ring[0])
            for xy in ring[1:]:
                path.lineTo(*xy)
            path.closeSubpath()
        return path

    @staticmethod
    def _stage_path(stage):
        path=QPainterPath()
        markers=[]
        for line in stage["paths"]:
            if len(line)==1:
                markers.append(line[0])
            else:
                path.moveTo(*line[0])
                for xy in line[1:]:
                    path.lineTo(*xy)
        return path,tuple(markers)

    def source_transform(self):
        # Native Qt affine transform; no per-vertex Python projection on repaint.
        origin=self.screen_at((0,0))
        scale=self.viewport.scale(self.plot_rect())
        sx,sy=self.work_frame.signs
        return QTransform(sx*scale,0,0,-sy*scale,origin.x(),origin.y())

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
            self.report_measurement()
        else:
            self.measurement_changed.emit("Select second point")
        self.update()

    def report_measurement(self):
        dx,dy,d=measure(*(self.work_frame.to_work(p) for p in self.measure_points))
        self.measurement_changed.emit(f"Distance {d:.3f} mm | dX {dx:.3f} | dY {dy:.3f}")

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
        elif self.viewport and self.picking_origin and event.button()==Qt.MouseButton.LeftButton:
            if QRectF(*self.plot_rect()).contains(event.position()):
                xy=self.origin_candidate(event.position(),bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
                self.origin_picked.emit(xy)
                self.cursor_changed.emit("Work X 0.000  Y 0.000 mm")
            event.accept()
        elif self.picking_origin and event.button()==Qt.MouseButton.RightButton:
            self.origin_cancelled.emit()
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
        if self.picking_origin:
            self.snap_preview=self.origin_candidate(event.position(),bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            self.update()
        self.cursor_changed.emit(self.cursor_label(event.position()))

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self._drag=None
            self.setCursor(Qt.CursorShape.CrossCursor) if self.picking_origin else self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def leaveEvent(self,event):
        self.snap_preview=None
        self.update()
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
        xmin,ymin,xmax,ymax=self.work_frame.bounds(self.source_bounds)
        scale=self.viewport.scale(self.plot_rect())
        point=self.screen_at
        p.save()
        plot=QRectF(*self.plot_rect())
        p.setClipRect(plot)
        if self.show_grid:
            step=self.viewport.grid_step(self.plot_rect())
            corners=[self.work_at(pt)
                     for pt in (plot.bottomLeft(),plot.topRight())]
            lo=tuple(min(a,b) for a,b in zip(*corners))
            hi=tuple(max(a,b) for a,b in zip(*corners))
            def work_point(xy):
                return point(self.work_frame.to_board(xy))
            p.setPen(QPen(QColor("#34475b"),0.8))
            for x in grid_values(lo[0],hi[0],step):
                p.drawLine(work_point((x,lo[1])),work_point((x,hi[1])))
            for y in grid_values(lo[1],hi[1],step):
                p.drawLine(work_point((lo[0],y)),work_point((hi[0],y)))
            p.setPen(QPen(QColor("#6b8198"),1.2))
            if lo[0]<=0<=hi[0]:
                p.drawLine(work_point((0,lo[1])),work_point((0,hi[1])))
            if lo[1]<=0<=hi[1]:
                p.drawLine(work_point((lo[0],0)),work_point((hi[0],0)))

        transform=self.source_transform()

        if project.outline and ("outline",0) not in self.hidden_layers:
            for cached in self._outline_paths:
                outline=transform.map(cached)
                p.fillPath(outline,QColor("#304c43"))
                p.setPen(QPen(QColor("#9ab7a5"),1.5))
                p.drawPath(outline)
        for i,layer in enumerate(project.copper):
            if ("copper",i) in self.hidden_layers:
                continue
            color=QColor("#dfb85d" if layer.side=="bottom" else "#df895c")
            color.setAlpha(210)
            for cached in self._copper_paths[i]:
                p.fillPath(transform.map(cached),color)
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
                cached,markers=self._cam_paths[i]
                p.drawPath(transform.map(cached))
                for xy in markers:
                    p.drawEllipse(point(xy),4,4)
            # Retention indicators are independent of cutout visibility.
            for i,gap in enumerate(self.cam["tab_gaps"],1):
                a,b=point(gap[0]),point(gap[-1])
                center=(a+b)/2
                p.setPen(QPen(QColor("#101a27"),9,Qt.PenStyle.SolidLine))
                p.drawLine(a,b)
                p.setPen(QPen(QColor("#ff668c"),5,Qt.PenStyle.SolidLine))
                p.drawLine(a,b)
                p.drawEllipse(center,6,6)
                p.drawText(center+QPointF(8,-8),f"T{i}")
        origin=point(self.work_frame.origin)
        sx,sy=1,1
        p.setPen(QPen(QColor("#56e0b2"),2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        # Axes in the work frame are always +X right, +Y up, even mirrored.
        lo=self.work_at(plot.bottomLeft())
        hi=self.work_at(plot.topRight())
        p.setPen(QPen(QColor("#56e0b2"),1,Qt.PenStyle.DashLine))
        if lo[0]<=0<=hi[0]:
            p.drawLine(QPointF(origin.x(),plot.top()),QPointF(origin.x(),plot.bottom()))
        if lo[1]<=0<=hi[1]:
            p.drawLine(QPointF(plot.left(),origin.y()),QPointF(plot.right(),origin.y()))
        p.setPen(QPen(QColor("#56e0b2"),2))
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
        if self.picking_origin and self.snap_preview is not None:
            target=point(self.snap_preview)
            p.setPen(QPen(QColor("#69b9ff"),2))
            p.drawEllipse(target,7,7)
            p.drawLine(target+QPointF(-10,0),target+QPointF(10,0))
            p.drawLine(target+QPointF(0,-10),target+QPointF(0,10))
        p.restore()
        p.setPen(QColor("#a8bacc"))
        if self.show_grid:
            step=self.viewport.grid_step(self.plot_rect())
            for x in grid_values(lo[0],hi[0],step):
                px=self.viewport.screen((x,0),self.plot_rect())[0]
                p.drawText(QPointF(px+2,plot.bottom()+13),f"{x:g}")
            for y in grid_values(lo[1],hi[1],step):
                py=self.viewport.screen((0,y),self.plot_rect())[1]
                p.drawText(QPointF(plot.left()+3,py-3),f"{y:g}")
        p.drawText(QPointF(20,25),"XY / CAM centerlines — work coordinates" if self.cam else "XY / Imported geometry — work coordinates")
        grid=f" | Work grid {self.viewport.grid_step(self.plot_rect()):g} mm" if self.show_grid else ""
        p.drawText(QPointF(20,self.height()-14),
                   f"Work bounds: X [{xmin:.3f}, {xmax:.3f}] Y [{ymin:.3f}, {ymax:.3f}] mm{grid}")
