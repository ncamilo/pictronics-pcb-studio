"""Capture the actual Qt window, using the offline platform in CI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
from PySide6.QtWidgets import QApplication
from pcb_studio.application.machine_service import MachineService
from pcb_studio.infrastructure.cnc.simulator import SimulatedMachine
from pcb_studio.presentation.window import create_window

app=QApplication([])
window=create_window(MachineService(SimulatedMachine()))
window.show()
window.load.click()
app.processEvents()
assert window.data is not None, window.message.text()
assert len(window.data["events"])==1472
out=Path(sys.argv[1])
out.mkdir(parents=True,exist_ok=True)
assert window.grab().save(str(out/"pcb_studio_desktop.png"))
print(f"Desktop capture: {window.width()}x{window.height()}, {len(window.data['events'])} events")
window.close()
