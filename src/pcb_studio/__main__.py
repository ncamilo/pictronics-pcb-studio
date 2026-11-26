def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Install the optional UI: python -m pip install -e ".[ui]"')
        return 1
    from pcb_studio.application.machine_service import MachineService
    from pcb_studio.infrastructure.cnc.simulator import SimulatedMachine
    from pcb_studio.presentation.window import create_window

    app = QApplication([])
    window = create_window(MachineService(SimulatedMachine()))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
