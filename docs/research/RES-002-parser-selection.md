# RES-002 — Gerber and Excellon parser selection

Status: preliminary comparison, not a benchmark or final dependency approval.

## Candidates
- FlatCAM Evo, pinned revision c948622f6b906f9910990d7bafbfb3012be21350: MIT root license; Gerber and Excellon parsers inherit Geometry and require application state. Reuse is explicitly retained as an option. Prefer extracting narrowly scoped helpers or an adapter rather than importing camlib wholesale.
- Gerbonara 1.6.3: https://pypi.org/project/gerbonara/1.6.3/ ; https://gerbolyze.gitlab.io/gerbonara/api-concepts.html . First prototype candidate because it offers Gerber and Excellon object APIs, explicit units, aperture macros, flashes, arcs and slots. Primitive-to-Shapely conversion and ordered polarity composition must be validated. Review package and transitive licenses before adoption.
- PyGerber: https://argmaster.github.io/pygerber/stable/ . MIT, Gerber X2/X3 focus; useful independent Gerber comparison. Excellon coverage not established.
- Gerbyx: https://github.com/TheAntTeam/gerbyx . MIT, direct Shapely geometry output advertised; coverage and maturity require testing, including Excellon.
- pcb-tools: https://github.com/curtacircuitos/pcb-tools . Legacy reference; not the preferred starting point.

## Proposed architecture
Parser ports return canonical millimetre geometry and diagnostics, not third-party application objects. Keep copper polygons (ordered dark/clear compositing), outline centerlines, drill centers and diameters, and routed slot centerlines distinct. Preserve source units, layer identity, plating if known, and coordinate origin. No implicit mirroring, recentering or scaling. Unsupported or ambiguous features must block toolpath generation.

## Validation gates
Synthetic fixtures: circular/rectangular/obround flashes, strokes, arcs, regions with holes, aperture macros, clear polarity, inch/mm equivalence, zero suppression, repeated drill tools, G85/routed slots, malformed inputs, and outline closure. Compare bounds, area, symmetric difference, hole centers/diameters and slot geometry against independently calculated expected values; use FlatCAM as a comparison, not sole oracle. Include realistic KiCad PWM 555 V2 fixtures when authorized. Benchmark elapsed time and peak memory separately from correctness. Define tessellation tolerance explicitly before comparing arcs.

## Decision
Prototype Gerbonara first; retain FlatCAM as reference and fallback implementation candidate. Prefer FlatCAM CAM algorithms for isolation, cutout and path ordering after dependency and license review. No third-party code or runtime dependency added in this research commit. Final selection requires passing fixtures and license audit.
