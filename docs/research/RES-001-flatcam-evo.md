# RES-001 — FlatCAM Evo source reconnaissance

Status: preliminary source inspection; no upstream code imported or executed.

## Provenance
Repository: https://github.com/MariusAdrian88/FlatCAM_Evo
Reviewed revision: c948622f6b906f9910990d7bafbfb3012be21350
License: root LICENSE is MIT, copyright Marius Stanciu (2018–2026) and Juan Pablo Caram (2014–2018). Verify individual file provenance and transitive dependencies before reuse.

## Inventory
Line counts include split trailing lines; coupling counts are literal self.app. occurrences, not a dependency graph.

| File | Lines | self.app. | Decision |
|---|---:|---:|---|
| appParsers/ParseGerber.py | 3988 | 148 | Compare standalone parser options before adapting; imports PyQt6, camlib, SVG/DXF helpers |
| appParsers/ParseExcellon.py | 1787 | 68 | Compare standalone alternatives; Geometry subclass with app constructor |
| camlib.py | 10348 | 276 | Do not vendor wholesale; extract only audited geometry helpers |
| appPlugins/ToolIsolation/IsolationGen.py | 1730 | 0 | Adapt selected algorithms; depends on camlib, AppDefaults, translation |
| appPlugins/ToolDrilling/DrillingGen.py | 341 | 0 | Adapt or independently implement grouping, slots and transforms; defaults and translation dependencies |
| appPlugins/ToolCutOut/CutOutGen.py | 1097 | 0 | Adapt contour and bridge algorithms; camlib, feature_access, translation dependencies |
| appCommon/PathOrder.py | 552 | 0 | Strong reuse candidate; NumPy/Shapely; nearest-neighbor plus 2-opt/Or-opt |
| appPlugins/Common/grbl/grbl_protocol.py | 438 | 0 | Strong reuse candidate; standard library only, explicit MIT header |
| appPlugins/Common/grbl/grbl_client.py | 1916 | 57 | Study stream_lines and operation ownership; mixin coupled to app/UI hooks, serial and translation |
| preprocessors/GRBL_11_no_M6.py | 244 | 0 | Reference for independent GRBL postprocessor; PreProc and parameter structure coupling |

## Architecture implications
FlatCAM Evo now includes GRBL sender components. Compare these with bCNC and the official GRBL interface before selecting a CNC implementation. Avoid introducing PyQt6 into the PySide6 application. Keep upstream implementation behind ports, normalize coordinates to mm and preserve source metadata. No implicit motion on connection. The absence of direct self.app references is not proof of independence.

## Next experiments
1. Inventory parser alternatives and Gerber/Excellon format coverage; test apertures, regions, polarity, arcs, unit/zero conventions, slots and invalid input.
2. Build synthetic fixtures, then compare with authorized PWM 555 V2 reference outputs.
3. Audit PathOrder and grbl_protocol dependencies, upstream tests and per-file provenance; record exact commit and license if imported.
4. Benchmark path order with direction constraints, unchanged cut geometry and deterministic output.
5. Test serial streaming in a fake transport: buffer accounting, errors, alarms, disconnect, hold/reset, uncertain motion and no automatic resume.
6. Define independent CAM contracts and numeric tolerances before implementation.

Acceptance: no silent unsupported features, no GUI dependencies in domain, no physical motion in research phase. No benchmarks or functional upstream tests have been performed yet.
