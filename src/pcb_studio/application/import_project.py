"""Assemble a read-only PCB preview through the import port."""
from pathlib import Path
from typing import Literal

from pcb_studio.domain.pcb import PCBProject
from pcb_studio.ports.pcb_import import PCBImporter


def import_project(importer: PCBImporter, name: str, *,
                   copper_files: tuple[tuple[Path, Literal["top", "bottom"]], ...],
                   drill_files: tuple[Path, ...] = (),
                   outline_file: Path | None = None) -> PCBProject:
    """Return a complete preview or raise; never publish a partial project."""
    if not name.strip() or not copper_files:
        raise ValueError("Project name and at least one copper file are required")
    sides = [side for _, side in copper_files]
    if len(set(sides)) != len(sides):
        raise ValueError("Duplicate copper side")
    copper = tuple(importer.copper(path, side) for path, side in copper_files)
    drills = tuple(importer.drills(path) for path in drill_files)
    outline = importer.outline(outline_file) if outline_file is not None else None
    return PCBProject(name, copper, drills, outline)
