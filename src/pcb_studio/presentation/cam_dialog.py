"""Explicit nominal geometry settings, not physical cutting parameters."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLabel,QComboBox,
    QDoubleSpinBox,QSpinBox,QLineEdit,QDialogButtonBox)


class CamDialog(QDialog):
    def __init__(self,project,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plan CAM geometry (offline)")
        layout=QVBoxLayout(self)
        info=QLabel("Illustrative geometry defaults only. Select one side. "
                    "Original XY is preserved; no mirroring, Z, feeds or machine commands.")
        info.setWordWrap(True)
        layout.addWidget(info)
        form=QFormLayout()
        self.side=QComboBox()
        self.side.addItem("Select copper side",None)
        for layer in project.copper:
            self.side.addItem(layer.side.title(),layer.side)
        if len(project.copper)==1:
            self.side.setCurrentIndex(1)
        form.addRow("Copper side",self.side)
        def number(label,value,lo,hi,decimals=3):
            field=QDoubleSpinBox()
            field.setDecimals(decimals)
            field.setRange(lo,hi)
            field.setValue(value)
            form.addRow(label,field)
            return field
        self.diameter=number("Effective isolation diameter (mm)",0.15,0.001,10)
        self.target=number("Target isolation width (mm)",0.15,0.003,10)
        self.passes=QSpinBox()
        self.passes.setRange(1,100)
        form.addRow("Isolation passes",self.passes)
        self.overlap=number("Overlap (%)",20,0,99.9,1)
        self.cutter=number("Cutout cutter diameter (mm)",1,0.001,10)
        self.margin=number("Assumed stock margin (mm)",3,0.001,100)
        self.anchors=QLineEdit()
        self.anchors.setPlaceholderText("x,y; x,y (optional, on original outline)")
        form.addRow("Tab anchors (canonical XY)",self.anchors)
        self.width=number("Tab width (mm)",2,0.001,20)
        layout.addLayout(form)
        layout.addWidget(QLabel("No anchors = no tabs; diagnostic is retained in the preview."))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generate preview")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selection(self):
        anchors=tuple(tuple(float(v.strip()) for v in part.split(","))
                      for part in self.anchors.text().split(";") if part.strip())
        return dict(side=self.side.currentData(),diameter=self.diameter.value(),
                    target=self.target.value(),passes=self.passes.value(),
                    overlap=self.overlap.value()/100,cutter=self.cutter.value(),
                    stock_margin=self.margin.value(),tab_anchors=anchors,tab_width=self.width.value())
