# RES-004 — First FlatCAM reuse and expanded parser experiments

Status: first reuse and expanded parser smoke tests passed; full geometry and hardware validation remain pending.

The GRBL protocol module at c948622f6b906f9910990d7bafbfb3012be21350 is the first vendored source. It imports only math and re and has an explicit MIT header. No changes to the upstream module. Independent tests cover status, invalid coordinates, offsets, probe results, errors and unit scaling. No serial access or machine commands. Full controller validation is still required; unknown states and stale offsets must never authorize motion. PathOrder is the next candidate; its NumPy/Shapely dependencies and directional constraints need separate tests. Do not import camlib wholesale.

Gerbonara tests now include rectangular/obround flashes, straight stroke, quarter arc, closed region, ordered polarity flags and routed slot. These validate primitive types, bounding boxes and order, not final copper composition, aperture macros, full outlines or numerical tessellation. See https://gerbolyze.gitlab.io/gerbonara/object-api.html. Independent expected values are analytic. No FlatCAM parser comparison has been run yet. Actual test outcomes must be recorded from CI.

Packaging: keep MIT text and provenance with vendored module; include license files in installed distribution. No production dependency selection or hardware integration is implied.

## Recorded CI evidence
- Initial commit 841bdb55647bbc0896fb33701567eff02d3d4db9: core CI passed all four jobs (23 tests passed, two optional parser modules skipped in the inspected Windows 3.12 log). https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45837005868
- Initial parser job: 9 passed and one failed on Ubuntu; Windows was cancelled by matrix fail-fast. The routed slot was parsed as a Line but ExcellonTool.equivalent_width expected a callable LengthUnit, not the string "mm". https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45837005859
- Fix 0fc7817b26852788dcfe61f9dd594bde713ac2bf: use gerbonara.utils.MM and correct the routed-slot header placement of G90. Expected geometry unchanged. All ten parser checks passed on Windows and Ubuntu; one warning remains in each job. https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45837242369
- Core CI also passed on the fix commit: https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45837242294
- Vendored GRBL protocol blob was verified to equal the original blob a67f8054fb64880f17104d280aa6729f5d614d80. No changes to source.

These results do not certify the full Gerber image, CAM safety, GRBL transport or real machine operation. No FlatCAM parser comparison yet. Next: independent copper area/polarity composition tests and parser adapter, plus audited PathOrder experiments.
