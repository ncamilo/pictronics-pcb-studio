"""Nominal per-stage process settings for offline NC visualization."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLabel,QDoubleSpinBox,
    QSpinBox,QTableWidget,QDialogButtonBox,QHeaderView)
from pcb_studio.domain.depth import DepthSetup
from pcb_studio.domain.tools import ProcessSettings


class NcDialog(QDialog):
    def __init__(self,job,parent=None,*,frame=None,saved=None):
        super().__init__(parent)
        self.setWindowTitle("Export NC preview — DO NOT RUN")
        self.resize(930,410)
        layout=QVBoxLayout(self)
        warning=QLabel("Offline visualization only. Active motion words; never run on a CNC. "
                       "Virtual cylindrical tools, configured work XY, no spindle commands. "
                       "Defaults are illustrative, not cutting recommendations.")
        warning.setWordWrap(True)
        layout.addWidget(warning)
        if frame is not None:
            layout.addWidget(QLabel(f'Work zero in source XY: {frame.origin} | Mirror: {frame.mirror} | All stages'))
        form=QFormLayout()
        def number(value,lo=0.001,hi=1000):
            box=QDoubleSpinBox()
            box.setDecimals(3)
            box.setRange(lo,hi)
            box.setValue(value)
            return box
        self.thickness=number(1.6)
        self.safe=number(3)
        self.breakthrough=number(0.1,0)
        for label,box in (("Nominal PCB thickness (mm)",self.thickness),
                          ("Nominal safe Z (mm)",self.safe),
                          ("Allowed breakthrough (mm)",self.breakthrough)):
            form.addRow(label,box)
        layout.addLayout(form)
        self.table=QTableWidget(len(job.stages),6)
        self.table.setHorizontalHeaderLabels(["Stage / diameter","Depth mm","Stepdown mm",
                                              "Plunge mm/min","XY mm/min","RPM metadata"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fields=[]
        for i,s in enumerate(job.stages):
            depth=0.1 if s.operation=="isolation" else 1.6
            step=0.1 if s.operation=="isolation" else 0.8
            widgets=[QLabel(f"{s.operation} / {s.diameter_mm:g}"),
                     number(depth),number(step),number(30),number(100),QSpinBox()]
            widgets[-1].setRange(1,100000)
            widgets[-1].setValue(10000)
            widgets[4].setEnabled(s.operation!="drill")
            for j,widget in enumerate(widgets):
                self.table.setCellWidget(i,j,widget)
            self.fields.append((s.operation,widgets[1:]))
        if saved is not None:
            setup,params=saved
            self.thickness.setValue(setup.thickness_mm)
            self.safe.setValue(setup.safe_z_mm)
            self.breakthrough.setValue(setup.breakthrough_limit_mm)
            for (_,fields),p in zip(self.fields,params):
                d,s,z,xy,rpm=fields
                d.setValue(p.depth_mm)
                s.setValue(p.max_stepdown_mm)
                z.setValue(p.plunge_mm_min)
                if p.feed_xy_mm_min is not None:
                    xy.setValue(p.feed_xy_mm_min)
                rpm.setValue(p.spindle_rpm)
        layout.addWidget(self.table)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Export offline previews")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selection(self):
        setup=DepthSetup(self.thickness.value(),self.safe.value(),self.breakthrough.value())
        settings=tuple(ProcessSettings(d.value(),s.value(),p.value(),rpm.value(),
                      None if op=="drill" else f.value())
                      for op,(d,s,p,f,rpm) in self.fields)
        return setup,settings
