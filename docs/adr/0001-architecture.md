# ADR 0001 — Monólito modular
Status: proposta inicial.
Contexto: integrar CAM e CNC sem acoplar domínio a GUI ou transporte.
Decisão: Python 3.11+, PySide6 opcional, arquitetura hexagonal; simulador antes de hardware. Licença GPL-3.0-or-later proposta para código original. Dependências externas serão auditadas antes de inclusão.
Consequências: mais contratos e testes iniciais, menor acoplamento; não se assume extração trivial de módulos upstream.
