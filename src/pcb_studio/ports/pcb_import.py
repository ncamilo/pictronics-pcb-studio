"""Import port independent of Gerbonara and Shapely."""
from pathlib import Path
from typing import Literal, Protocol
from pcb_studio.domain.pcb import BoardOutline, PanelOutline, CopperLayer, DrillLayer


class PCBImportError(ValueError):
    """Unsupported or invalid PCB input."""


class PCBImporter(Protocol):
    def copper(self, path: Path, side: Literal["top", "bottom"]) -> CopperLayer: ...
    def drills(self, path: Path) -> DrillLayer: ...
    def outline(self, path: Path) -> BoardOutline | PanelOutline: ...
