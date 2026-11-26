from dataclasses import dataclass
from enum import Enum


class MachineState(str, Enum):
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    ALARM = "alarm"


@dataclass(frozen=True)
class MachineStatus:
    state: MachineState
    simulated: bool = True
