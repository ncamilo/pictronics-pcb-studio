from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
from pcb_studio.application.machine_service import MachineService


def create_window(service: MachineService) -> QWidget:
    window = QWidget()
    window.setWindowTitle("Pictronics PCB Studio — v0.0.1")
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("Modo simulado — sem hardware real"))
    status = QLabel(service.status().state.value)
    layout.addWidget(status)
    connect = QPushButton("Conectar simulador")
    disconnect = QPushButton("Desconectar simulador")
    connect.clicked.connect(lambda: status.setText(service.connect().state.value))
    disconnect.clicked.connect(lambda: status.setText(service.disconnect().state.value))
    layout.addWidget(connect)
    layout.addWidget(disconnect)
    window.resize(480, 240)
    return window
