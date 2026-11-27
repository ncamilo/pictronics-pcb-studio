"""Capture actual imported geometry in Qt offscreen."""
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
w.show()
root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
assert w.import_files(name="Synthetic board 30 x 20 mm",bottom=str(root/"bottom.gbr"),
                      drills=(str(root/"drills.drl"),),outline=str(root/"outline.gbr")),w.message.text()
w.measure.setChecked(True)
w.board.measure_at((5,10))
w.board.measure_at((25,10))
app.processEvents()
out=Path(sys.argv[1])
out.mkdir(parents=True,exist_ok=True)
assert w.grab().save(str(out/"pcb_import_desktop.png"))
print(f"Imported capture: {len(w.project.copper)} copper layer; {len(w.project.drills[0].drills)} holes")
w.close()
