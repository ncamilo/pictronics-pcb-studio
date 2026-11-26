"""Work origin and reflection in the canonical source frame."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLabel,QComboBox,
                               QDoubleSpinBox,QDialogButtonBox)
from pcb_studio.domain.work_frame import WorkFrame,corner_frame


class WorkFrameDialog(QDialog):
    def __init__(self,board_bounds,stock_bounds,frame,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Work XY setup (offline)")
        self.board_bounds=board_bounds
        self.stock_bounds=stock_bounds
        layout=QVBoxLayout(self)
        note=QLabel("Origin is a point in original Gerber XY. Mirror X reverses X; "
                    "Mirror Y reverses Y. Reflection is through the origin, not an "
                    "automatic board flip. It reverses path direction. Physical registration is not verified.")
        note.setWordWrap(True)
        layout.addWidget(note)
        form=QFormLayout()
        self.preset=QComboBox()
        for label,key in (("Custom / current","custom"),("Board corner (positive XY)","board"),
                          ("Stock corner (positive XY)","stock"),("Board center","center"),
                          ("Original Gerber zero","original")):
            if key!="stock" or stock_bounds is not None:
                self.preset.addItem(label,key)
        self.mirror=QComboBox()
        for label,key in (("None","none"),("Mirror X (reverse X)","x"),("Mirror Y (reverse Y)","y")):
            self.mirror.addItem(label,key)
        self.mirror.setCurrentIndex(self.mirror.findData(frame.mirror))
        self.x=QDoubleSpinBox()
        self.y=QDoubleSpinBox()
        for box,value in zip((self.x,self.y),frame.origin):
            box.setDecimals(6)
            box.setRange(-1000000,1000000)
            box.setValue(value)
        for label,widget in (("Origin preset",self.preset),("Reflection",self.mirror),
                             ("Original X (mm)",self.x),("Original Y (mm)",self.y)):
            form.addRow(label,widget)
        self.preset.currentIndexChanged.connect(self.refresh)
        self.mirror.currentIndexChanged.connect(self.refresh)
        layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh(self,*_):
        key=self.preset.currentData()
        mirror=self.mirror.currentData()
        self.x.setEnabled(key=="custom")
        self.y.setEnabled(key=="custom")
        if key=="custom":
            return
        if key in ("board","stock"):
            xy=corner_frame(self.board_bounds if key=="board" else self.stock_bounds,mirror).origin
        elif key=="center":
            a,b,c,d=self.board_bounds
            xy=((a+c)/2,(b+d)/2)
        else:
            xy=(0,0)
        self.x.setValue(xy[0])
        self.y.setValue(xy[1])

    def selection(self):
        key=self.preset.currentData()
        mirror=self.mirror.currentData()
        if key in ("board","stock"):
            return corner_frame(self.board_bounds if key=="board" else self.stock_bounds,mirror)
        if key=="center":
            a,b,c,d=self.board_bounds
            return WorkFrame(((a+c)/2,(b+d)/2),mirror)
        return WorkFrame((self.x.value(),self.y.value()),mirror)
