# Pictronics PCB Studio

Open-source PCB milling workstation: from Gerber/Excellon to CNC fabrication.

Estado: **v0.0.1 — fundação arquitetural**, sem controle de hardware real ou motor CAM implementado.

## Desenvolvimento (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ui]"
python -m pytest
python -m pcb_studio
```

A interface inicial é apenas demonstrativa. Sem conexão serial, spindle ou movimentação física.

## Documentação
- [Arquitetura](docs/ARCHITECTURE.md)
- [Requisitos](docs/REQUIREMENTS.md)
- [Roadmap](docs/ROADMAP.md)
- [Referências e estratégia de reutilização](docs/UPSTREAM.md)
- [Segurança](docs/SAFETY.md)
- [Decisões arquiteturais](docs/adr/0001-architecture.md)

Licença proposta para o código original: GPL-3.0-or-later. Nenhum código de terceiros foi importado nesta versão.
