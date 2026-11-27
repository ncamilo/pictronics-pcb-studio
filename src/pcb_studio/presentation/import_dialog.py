"""Explicit file roles, without automatic coordinate transforms."""
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,
    QPushButton,QHBoxLayout,QFileDialog,QLabel,QDialogButtonBox,QListWidget)


class ImportDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import PCB files")
        self.resize(650,360)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("Select Gerber copper layers and outline, plus Excellon drills."))
        form=QFormLayout()
        self.name=QLineEdit("Imported PCB")
        form.addRow("Project name",self.name)
        self.top=self._file_row(form,"Top copper")
        self.bottom=self._file_row(form,"Bottom copper")
        self.outline=self._file_row(form,"Board outline")
        self.drills=QListWidget()
        form.addRow("Drill files",self.drills)
        row=QHBoxLayout()
        add=QPushButton("Add drill files")
        clear=QPushButton("Clear drills")
        add.clicked.connect(self._add_drills)
        clear.clicked.connect(self.drills.clear)
        row.addWidget(add)
        row.addWidget(clear)
        form.addRow(row)
        layout.addLayout(form)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _file_row(self,form,label):
        edit=QLineEdit()
        browse=QPushButton("Browse")
        def choose():
            path,_=QFileDialog.getOpenFileName(self,label,"","Gerber (*.gbr *.ger *.gtl *.gbl *.gko);;All files (*)")
            if path:
                edit.setText(path)
        browse.clicked.connect(choose)
        row=QHBoxLayout()
        row.addWidget(edit)
        row.addWidget(browse)
        form.addRow(label,row)
        return edit

    def _add_drills(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Excellon drill files","","Drill files (*.drl *.xln *.exc);;All files (*)")
        existing={self.drills.item(i).text() for i in range(self.drills.count())}
        for path in paths:
            if path not in existing:
                self.drills.addItem(path)
                existing.add(path)

    def selection(self):
        return dict(name=self.name.text().strip(),top=self.top.text().strip(),
                    bottom=self.bottom.text().strip(),outline=self.outline.text().strip(),
                    drills=tuple(self.drills.item(i).text() for i in range(self.drills.count())))
