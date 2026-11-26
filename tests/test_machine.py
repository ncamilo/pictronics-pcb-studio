from pcb_studio.application.machine_service import MachineService
from pcb_studio.domain.machine import MachineState
from pcb_studio.infrastructure.cnc.simulator import SimulatedMachine


def test_initial_state():
    service = MachineService(SimulatedMachine())
    assert service.status().state is MachineState.DISCONNECTED
    assert service.status().simulated


def test_connection_lifecycle():
    service = MachineService(SimulatedMachine())
    assert service.connect().state is MachineState.IDLE
    assert service.disconnect().state is MachineState.DISCONNECTED


def test_connect_is_idempotent():
    service = MachineService(SimulatedMachine())
    assert service.connect() == service.connect()


def test_instances_are_independent():
    first = MachineService(SimulatedMachine())
    second = MachineService(SimulatedMachine())
    first.connect()
    assert second.status().state is MachineState.DISCONNECTED
