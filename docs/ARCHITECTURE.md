# Arquitetura
Monólito modular, portas e adaptadores. Domínio em Python puro. Application depende do domínio e de contratos; infraestrutura implementa contratos; apresentação depende dos casos de uso; composition root injeta dependências.

Módulos planejados: CAM (parser, geometria, isolamento, furação, contorno), CNC (protocolo, streaming, estados), probing (mapa de altura), visualização, persistência, workflow. Os pacotes vazios representam fronteiras futuras, não funcionalidades prontas.

Decisões: unidades internas em mm; coordenadas e origem explícitas; modelos imutáveis quando possível; comunicação de hardware fora da thread gráfica; streaming incremental com backpressure; renderização em lotes, sem um widget por segmento. Eventos de máquina e logs separados do renderizador. Nenhum comando físico no MVP inicial.

Testes: unidade no domínio, contrato de adaptadores, integração com simulador, golden files Gerber/Excellon, testes de desempenho com G-code de 8 MB, depois bancada com máquina real. O simulador inicial é propositalmente simples e não representa a cinemática ou o firmware GRBL.
