from pcb_studio.domain.machine import MachineStatus
from pcb_studio.ports.machine import MachinePort


class MachineService:
    def __init__(self, machine: MachinePort) -> None:
        self._machine = machine

    def connect(self) -> MachineStatus:
        self._machine.connect()
        return self._machine.status()

    def disconnect(self) -> MachineStatus:
        self._machine.disconnect()
        return self._machine.status()

    def status(self) -> MachineStatus:
        return self._machine.status()
