# Referências upstream
Nenhum código foi copiado. Licenças por arquivo e commit ainda devem ser verificadas.

| Projeto | Estratégia |
|---|---|
| https://github.com/MariusAdrian88/FlatCAM_Evo | Auditar parsers e operações geométricas; adaptar componentes maduros se compatíveis |
| https://github.com/vlachoudis/bCNC | Estudar comportamento de streaming, probing, alarmes e estados; implementação independente baseada na especificação GRBL |
| https://github.com/ToxaToxaToxa/G-PCB | Estudar fluxo de fabricação; desenvolver interface e orquestração próprias |
| https://github.com/aazriel/pcbtracemill | Estudar simulação e arquitetura; avaliar adaptação de componentes compatíveis |
| https://github.com/pcb2gcode/pcb2gcode | Referência de resultados e validação cruzada |
| https://github.com/gnea/grbl | Especificação primária do protocolo |

Reimplementação independente não significa tradução linha a linha. Documentar comportamento público e testes, escrever código original e evitar copiar estrutura expressiva. Para componentes importados, registrar commit, caminho, licença, autoria e modificações. GPL-2.0-only não deve ser incorporada em uma obra GPL-3.0 sem autorização compatível.
