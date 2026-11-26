# RES-004 — First FlatCAM reuse and expanded parser experiments

Status: implementation submitted for CI; results pending.

The GRBL protocol module at c948622f6b906f9910990d7bafbfb3012be21350 is the first vendored source. It imports only math and re and has an explicit MIT header. No changes to the upstream module. Independent tests cover status, invalid coordinates, offsets, probe results, errors and unit scaling. No serial access or machine commands. Full controller validation is still required; unknown states and stale offsets must never authorize motion. PathOrder is the next candidate; its NumPy/Shapely dependencies and directional constraints need separate tests. Do not import camlib wholesale.

Gerbonara tests now include rectangular/obround flashes, straight stroke, quarter arc, closed region, ordered polarity flags and routed slot. These validate primitive types, bounding boxes and order, not final copper composition, aperture macros, full outlines or numerical tessellation. See https://gerbolyze.gitlab.io/gerbonara/object-api.html. Independent expected values are analytic. No FlatCAM parser comparison has been run yet. Actual test outcomes must be recorded from CI.

Packaging: keep MIT text and provenance with vendored module; include license files in installed distribution. No production dependency selection or hardware integration is implied.
