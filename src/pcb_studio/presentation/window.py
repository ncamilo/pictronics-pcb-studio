"""Offline desktop workstation. No physical machine actions."""
from pathlib import Path
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QStackedWidget, QDialog, QFileDialog,
)
from pcb_studio.application.machine_service import MachineService
from pcb_studio.presentation.toolpath_widget import ToolpathWidget
from pcb_studio.presentation.board_widget import BoardWidget
from pcb_studio.presentation.import_dialog import ImportDialog
from pcb_studio.presentation.cam_dialog import CamDialog
from pcb_studio.presentation.nc_dialog import NcDialog
from pcb_studio.domain.work_frame import WorkFrame,corner_frame
from pcb_studio.presentation.work_frame_dialog import WorkFrameDialog


def _demo_loader():
    from pcb_studio.infrastructure.cam.demo import build_demo
    return build_demo(Path(__file__).resolve().parents[3]/"examples"/"synthetic_board")


class StudioWindow(QWidget):
    def __init__(self, service, demo_loader=None):
        super().__init__()
        self.service=service
        self.demo_loader=demo_loader or _demo_loader
        self.data=None
        self.project=None
        self.cam_geometry=None
        self.cam_job=None
        self.work_frame=WorkFrame()
        self.setWindowTitle("Pictronics PCB Studio — Offline workstation")
        self.resize(1120,760)
        self.setStyleSheet("""
            QWidget { background: #101a27; color: #e5edf6; font-size: 13px; }
            QLabel { background: transparent; }
            QFrame#panel, QTreeWidget { background: #1c2b3d; border: 1px solid #33465c; border-radius: 5px; }
            QPushButton, QComboBox { background: #293e54; padding: 7px; border: 1px solid #526981; border-radius: 4px; }
            QPushButton:disabled { color: #718196; background: #1c2b3d; }
            QTreeWidget::item { padding: 5px; }
            QHeaderView::section { background: #26384c; padding: 4px; }
        """)
        layout=QVBoxLayout(self)
        title=QLabel("Pictronics PCB Studio  /  CAM preview")
        title.setStyleSheet("font-size: 22px; font-weight: bold; padding: 6px;")
        layout.addWidget(title)
        bar=QHBoxLayout()
        self.load=QPushButton("Load synthetic board")
        self.load.clicked.connect(self.load_demo)
        bar.addWidget(self.load)
        self.import_button=QPushButton("Import PCB files")
        self.import_button.clicked.connect(self.open_import)
        bar.addWidget(self.import_button)
        self.plan_cam=QPushButton("Plan CAM preview")
        self.plan_cam.clicked.connect(self.open_cam)
        bar.addWidget(self.plan_cam)
        self.save_cam=QPushButton("Export CAM JSON")
        self.save_cam.clicked.connect(self.export_cam)
        bar.addWidget(self.save_cam)
        self.save_nc=QPushButton("Export NC preview")
        self.save_nc.clicked.connect(self.open_nc)
        bar.addWidget(self.save_nc)
        bar.addStretch()
        bar.addWidget(QLabel("OFFLINE ONLY  |  Hardware disabled"))
        layout.addLayout(bar)
        split=QSplitter(Qt.Orientation.Horizontal)
        self.tree=QTreeWidget()
        self.tree.setHeaderLabels(["Project / CAM stages"])
        split.addWidget(self.tree)
        self.canvas=ToolpathWidget()
        self.board=BoardWidget()
        self.views=QStackedWidget()
        self.views.addWidget(self.canvas)
        self.views.addWidget(self.board)
        split.addWidget(self.views)
        self.tree.itemChanged.connect(self.layer_changed)
        panel=QFrame()
        panel.setObjectName("panel")
        right=QVBoxLayout(panel)
        right.addWidget(QLabel("SIMULATED TOOL POSITION"))
        self.coords=QLabel("X  —\nY  —\nZ  —")
        self.coords.setStyleSheet("font-family: monospace; font-size: 20px; color: #69b9ff; padding: 8px;")
        right.addWidget(self.coords)
        self.detail=QLabel("No preview loaded")
        self.detail.setWordWrap(True)
        right.addWidget(self.detail)
        self.diagnostics=QLabel("Diagnostics: —")
        self.diagnostics.setWordWrap(True)
        right.addWidget(self.diagnostics)
        right.addStretch()
        right.addWidget(QLabel("MACHINE SIMULATOR"))
        self.status=QLabel(service.status().state.value)
        right.addWidget(self.status)
        connect=QPushButton("Connect simulator")
        disconnect=QPushButton("Disconnect simulator")
        connect.clicked.connect(lambda: self.status.setText(service.connect().state.value))
        disconnect.clicked.connect(lambda: self.status.setText(service.disconnect().state.value))
        right.addWidget(connect)
        right.addWidget(disconnect)
        split.addWidget(panel)
        split.setSizes([205,680,235])
        layout.addWidget(split,1)
        self.inspect_bar=QFrame()
        inspect=QHBoxLayout(self.inspect_bar)
        inspect.setContentsMargins(0,0,0,0)
        self.fit=QPushButton("Fit to View")
        self.fit.clicked.connect(self.board.fit_view)
        self.work_setup=QPushButton("Work XY setup")
        self.work_setup.clicked.connect(self.open_work_frame)
        self.work_label=QLabel("Work XY: original")
        self.work_label.setWordWrap(True)
        right.insertWidget(3,self.work_label)
        self.grid=QCheckBox("Grid")
        self.grid.setChecked(True)
        self.grid.toggled.connect(self.board.set_grid)
        self.measure=QCheckBox("Measure")
        self.measure.toggled.connect(self.board.set_measure)
        self.cursor=QLabel("Cursor: —")
        self.measurement=QLabel("Measurement: —")
        self.board.cursor_changed.connect(self.cursor.setText)
        self.board.measurement_changed.connect(self.measurement.setText)
        for widget in (self.fit,self.work_setup,self.grid,self.measure,self.cursor,self.measurement):
            inspect.addWidget(widget)
        inspect.addStretch()
        layout.addWidget(self.inspect_bar)
        self.inspect_bar.hide()
        controls=QHBoxLayout()
        self.previous=QPushButton("Previous")
        self.next=QPushButton("Next")
        self.slider=QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0,0)
        self.previous.clicked.connect(lambda: self.slider.setValue(self.slider.value()-1))
        self.next.clicked.connect(lambda: self.slider.setValue(self.slider.value()+1))
        self.slider.valueChanged.connect(self.refresh)
        self.stage=QComboBox()
        self.stage.addItem("All stages",None)
        self.stage.currentIndexChanged.connect(self.refresh)
        self.rapid=QCheckBox("Rapid travel")
        self.rapid.setChecked(True)
        self.rapid.toggled.connect(self.refresh)
        for widget in (self.previous,self.slider,self.next,self.stage,self.rapid):
            controls.addWidget(widget)
        controls.setStretch(1,1)
        layout.addLayout(controls)
        self.message=QLabel("Ready to load offline demonstration.")
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.refresh()

    def load_demo(self):
        try:
            data=self.demo_loader()
        except Exception as exc:
            self.message.setText(f"Demo load failed: {exc}. Install CAM dependencies and use a source checkout.")
            return
        self.set_preview(data)

    def set_preview(self,data):
        self.project=None
        self.cam_geometry=None
        self.cam_job=None
        self.work_frame=WorkFrame()
        self.work_label.setText("Work XY: demo coordinates")
        self.inspect_bar.hide()
        self.views.setCurrentWidget(self.canvas)
        self.data=data
        self.canvas.set_data(data)
        self.tree.clear()
        root=QTreeWidgetItem(self.tree,[data["name"]])
        self.stage.blockSignals(True)
        self.stage.clear()
        self.stage.addItem("All stages",None)
        for i,s in enumerate(data["stages"]):
            item=QTreeWidgetItem(root,[f'{s["label"]} / {s["tool"]}'])
            item.setForeground(0,QColor(s["color"]))
            self.stage.addItem(s["label"],i)
        root.setExpanded(True)
        self.stage.blockSignals(False)
        self.slider.setRange(0,len(data["events"]))
        self.slider.setValue(len(data["events"]))
        self.diagnostics.setText("Diagnostics:\n"+("\n".join(data["diagnostics"]) or "None reported"))
        self.message.setText(f'{data["moves"]} movements | Nominal centerlines only | Not manufacturing-ready')
        self.refresh()

    def open_import(self):
        dialog=ImportDialog(self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.import_files(**dialog.selection())

    def import_files(self, *, name, top="", bottom="", outline="", drills=()):
        try:
            from pcb_studio.application.import_project import import_project
            from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
            copper=tuple((Path(path),side) for path,side in ((top,"top"),(bottom,"bottom")) if path)
            paths=[p for p,_ in copper]+[Path(p) for p in drills]+([Path(outline)] if outline else [])
            if len({p.resolve() for p in paths})!=len(paths):
                raise ValueError("A file cannot be assigned more than once")
            project=import_project(GerbonaraImporter(),name,copper_files=copper,
                                   drill_files=tuple(Path(p) for p in drills),
                                   outline_file=Path(outline) if outline else None)
        except Exception as exc:
            self.message.setText(f"Import failed: {exc}")
            return False
        self.set_project(project)
        return True

    def set_project(self,project):
        self.data=None
        self.project=project
        self.cam_geometry=None
        self.cam_job=None
        self.measure.setChecked(False)
        self.board.set_project(project)
        self.set_work_frame(corner_frame(self.outline_bounds()) if project.outline else WorkFrame())
        self.inspect_bar.show()
        self.views.setCurrentWidget(self.board)
        self.tree.blockSignals(True)
        self.tree.clear()
        root=QTreeWidgetItem(self.tree,[project.name])
        entries=[(("copper",i),f"{layer.side.title()} copper / {len(layer.polygons)} polygons")
                 for i,layer in enumerate(project.copper)]
        entries += [(("drill",i),f"Drill layer / {len(layer.drills)} holes / {len(layer.slots)} slots")
                    for i,layer in enumerate(project.drills)]
        if project.outline:
            entries.append((("outline",0),"Board outline"))
        for key,label in entries:
            item=QTreeWidgetItem(root,[label])
            item.setData(0,Qt.ItemDataRole.UserRole,key)
            item.setCheckState(0,Qt.CheckState.Checked)
        root.setExpanded(True)
        self.tree.blockSignals(False)
        self.slider.setRange(0,0)
        self.stage.clear()
        self.stage.addItem("No CAM plan",None)
        self.coords.setText("X  —\nY  —\nZ  —")
        self.detail.setText("Imported geometry only")
        self.diagnostics.setText("CAM not planned"+("\nOutline not supplied" if project.outline is None else ""))
        self.message.setText("Import complete | No toolpaths generated | Not manufacturing-ready")
        self.refresh()

    def outline_bounds(self):
        xs,ys=zip(*self.project.outline.exterior)
        return min(xs),min(ys),max(xs),max(ys)

    def set_work_frame(self,frame):
        self.work_frame=frame
        self.board.set_work_frame(frame)
        x,y=frame.origin
        self.work_label.setText(f"Work zero: source ({x:.3f}, {y:.3f}) mm | Mirror: {frame.mirror}")

    def open_work_frame(self):
        if self.project is None or self.project.outline is None:
            return
        stock=tuple(self.cam_geometry["stock_bounds"]) if self.cam_geometry else None
        dialog=WorkFrameDialog(self.outline_bounds(),stock,self.work_frame,self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.set_work_frame(dialog.selection())
            self.message.setText("Work XY updated | Source view unchanged | Applies to all exported stages")

    def open_cam(self):
        if self.project is None:
            return
        dialog=CamDialog(self.project,self)
        if self.cam_geometry is not None:
            s=self.cam_geometry['settings']
            dialog.side.setCurrentIndex(dialog.side.findData(self.cam_geometry['side']))
            dialog.diameter.setValue(s['effective_isolation_diameter_mm'])
            dialog.target.setValue(s['target_width_mm'])
            dialog.passes.setValue(s['passes'])
            dialog.overlap.setValue(s['overlap']*100)
            dialog.cutter.setValue(s['cutout_diameter_mm'])
            dialog.margin.setValue(s['stock_margin_mm'])
            dialog.width.setValue(s['tab_width_mm'])
            dialog.anchors.setText('; '.join(f'{x!r},{y!r}' for x,y in s['tab_anchors']))
        if dialog.exec()==QDialog.DialogCode.Accepted:
            try:
                settings=dialog.selection()
            except ValueError as exc:
                self.message.setText(f"CAM settings failed: {exc}")
                return
            self.generate_cam(**settings)

    def generate_cam(self,**settings):
        try:
            from pcb_studio.infrastructure.cam.geometry_job import plan_geometry_job
            result,job=plan_geometry_job(self.project,**settings)
        except Exception as exc:
            self.message.setText(f"CAM preview failed: {exc}")
            return False
        if self.cam_geometry and self.cam_geometry['side']!=result['side']:
            # Explicitly select reflection again for the new side.
            self.set_work_frame(WorkFrame(self.work_frame.origin))
        self.cam_geometry=result
        self.cam_job=job
        self.board.set_cam(result)
        root=self.tree.topLevelItem(0)
        self.tree.blockSignals(True)
        for i in reversed(range(root.childCount())):
            key=root.child(i).data(0,Qt.ItemDataRole.UserRole)
            if key and key[0]=="cam":
                root.takeChild(i)
        for i,s in enumerate(result["stages"]):
            item=QTreeWidgetItem(root,[f'{s["operation"]} / {s["diameter_mm"]:g} mm / {s["feature_count"]}'])
            item.setData(0,Qt.ItemDataRole.UserRole,("cam",i))
            item.setCheckState(0,Qt.CheckState.Checked)
        # Hide the opposite copper layer, not its underlying data.
        for i,layer in enumerate(self.project.copper):
            key=("copper",i)
            if layer.side!=result["side"]:
                self.board.hidden_layers.add(key)
            else:
                self.board.hidden_layers.discard(key)
            root.child(i).setCheckState(0,Qt.CheckState.Unchecked if key in self.board.hidden_layers else Qt.CheckState.Checked)
        root.setExpanded(True)
        self.tree.blockSignals(False)
        self.board.update()
        self.detail.setText(f'CAM geometry / {result["side"]} / {len(result["stages"])} stages')
        self.diagnostics.setText("Diagnostics:\n"+("\n".join(d["code"] for d in result["diagnostics"]) or "None reported"))
        self.message.setText(f'CAM preview complete | residual {result["isolation_residual_mm2"]:.4f} mm2 | OFFLINE ONLY')
        self.refresh()
        return True

    def write_cam_json(self,path):
        if self.cam_geometry is None:
            raise ValueError("No CAM preview")
        if not str(path).lower().endswith(".cam.json"):
            raise ValueError("Use .cam.json for offline geometry")
        Path(path).write_text(json.dumps(self.cam_geometry,indent=2,allow_nan=False)+"\n",encoding="utf-8")

    def export_cam(self):
        if self.cam_geometry is None:
            return
        path,_=QFileDialog.getSaveFileName(self,"Export offline CAM geometry","preview.cam.json","CAM geometry (*.cam.json)")
        if path:
            try:
                self.write_cam_json(path if path.lower().endswith(".cam.json") else path+".cam.json")
            except (OSError,ValueError) as exc:
                self.message.setText(f"Export failed: {exc}")
                return
            self.message.setText("CAM JSON exported | Not G-code or a machine program")

    def open_nc(self):
        if self.cam_job is None:
            return
        dialog=NcDialog(self.cam_job,self,frame=self.work_frame)
        if dialog.exec()!=QDialog.DialogCode.Accepted:
            return
        try:
            setup,settings=dialog.selection()
        except ValueError as exc:
            self.message.setText(f"NC settings failed: {exc}")
            return
        directory=QFileDialog.getExistingDirectory(self,"Export offline NC previews to folder")
        if directory:
            self.write_nc_previews(directory,setup,settings)

    def write_nc_previews(self,directory,setup,settings):
        try:
            from pcb_studio.infrastructure.cam.nc_stage_preview import export_stage_nc
            if self.cam_job is None:
                raise ValueError("No CAM geometry planned")
            folder=export_stage_nc(directory,self.cam_job,setup,settings,
                                  start_xy=tuple(self.cam_geometry["stock_bounds"][:2]),frame=self.work_frame)
        except Exception as exc:
            self.message.setText(f"NC preview failed: {exc}")
            return None
        self.message.setText(f"Offline NC previews saved: {folder} | DO NOT RUN ON CNC")
        return folder

    def layer_changed(self,item,column):
        if self.project is None:
            return
        key=item.data(0,Qt.ItemDataRole.UserRole)
        if key is not None:
            key=tuple(key)
            if item.checkState(0)==Qt.CheckState.Checked:
                self.board.hidden_layers.discard(key)
            else:
                self.board.hidden_layers.add(key)
            self.board.update()

    def refresh(self,*_):
        self.work_setup.setEnabled(self.project is not None and self.project.outline is not None)
        self.plan_cam.setEnabled(self.project is not None and self.project.outline is not None)
        self.save_cam.setEnabled(self.cam_geometry is not None)
        self.save_nc.setEnabled(self.cam_job is not None)
        self.previous.setEnabled(self.data is not None and self.slider.value()>0)
        self.next.setEnabled(self.data is not None and self.slider.value()<self.slider.maximum())
        for control in (self.slider,self.stage,self.rapid):
            control.setEnabled(self.data is not None)
        if self.data is None:
            return
        n=self.slider.value()
        self.canvas.step=n
        self.canvas.stage_filter=self.stage.currentData()
        self.canvas.show_rapid=self.rapid.isChecked()
        e=self.data["events"][n-1] if n else None
        v=e["b"] if e else self.data["initial"]
        self.coords.setText("\n".join(f"{axis} {value:9.3f}" for axis,value in zip("XYZ",v)))
        label=self.data["stages"][e["stage"]]["label"]+" / "+e["kind"] if e else "Start"
        self.detail.setText(f'{n}/{len(self.data["events"])} events\n{label}')
        self.canvas.update()


def create_window(service: MachineService, demo_loader=None) -> QWidget:
    return StudioWindow(service,demo_loader)
