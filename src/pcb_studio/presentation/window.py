"""Offline desktop workstation. No physical machine actions."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame, QStackedWidget, QDialog,
)
from pcb_studio.application.machine_service import MachineService
from pcb_studio.presentation.toolpath_widget import ToolpathWidget
from pcb_studio.presentation.board_widget import BoardWidget
from pcb_studio.presentation.import_dialog import ImportDialog


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
        self.board.set_project(project)
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
