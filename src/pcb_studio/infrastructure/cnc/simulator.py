from pcb_studio.domain.machine import MachineState, MachineStatus


class SimulatedMachine:
    """Minimal connection/status fake, never performs physical motion."""

    def __init__(self) -> None:
        self._state = MachineState.DISCONNECTED

    def connect(self) -> None:
        if self._state == MachineState.DISCONNECTED:
            self._state = MachineState.IDLE

    def disconnect(self) -> None:
        self._state = MachineState.DISCONNECTED

    def status(self) -> MachineStatus:
        return MachineStatus(self._state)
