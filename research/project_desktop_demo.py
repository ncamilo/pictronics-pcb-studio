"""Capture actual board CAM preview with labeled retention gaps."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from pcb_studio.application.machine_service import MachineService
from pcb_studio.infrastructure.cnc.simulator import SimulatedMachine
from pcb_studio.presentation.window import create_window

app=QApplication([])
w=create_window(MachineService(SimulatedMachine()))
w.resize(1450,850)
w.show()
root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
assert w.import_files(name="Synthetic board 30 x 20 mm",bottom=str(root/"bottom.gbr"),
                      drills=(str(root/"drills.drl"),),outline=str(root/"outline.gbr")),w.message.text()
assert w.generate_cam(side="bottom",diameter=0.15,target=0.15,passes=1,overlap=0.2,
    cutter=1,stock_margin=3,tab_anchors=((15,0),(30,10),(15,20),(0,10)),tab_width=2),w.message.text()
out=Path(sys.argv[1])
out.mkdir(parents=True,exist_ok=True)
w.write_project(out/"synthetic.pcbstudio.json")
assert w.read_project(out/"synthetic.pcbstudio.json"),w.message.text()
app.processEvents()
assert w.grab().save(str(out/"pcb_project_tabs.png"))
w.close()
