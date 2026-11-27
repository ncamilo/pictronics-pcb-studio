# Roadmap

Current baseline: offline desktop import, CAM preview, NC preview export and explicit work XY frame. Real PWM 555 V2 files imported and NC opened in bCNC; physical execution is not enabled.

See [RES-032 — upstream feature study](research/RES-032-feature-roadmap.md) for source-level comparison, acceptance gates and proposed priorities.

- [x] Initial structure, contracts, simulator and CI.
- [x] Research snapshots, synthetic fixtures, selected FlatCAM reference comparisons.
- [x] Experimental Gerber/Excellon import, native geometry preview, isolation/drill/cutout, tool and XYZ models, NC readback and offline export.
- [ ] Graphical tabs, versioned project persistence, work-frame preview and physical double-side registration.
- [ ] Physical tool/recipe UI, CAM quality and conservative path optimization.
- [ ] Offline CNC preflight, modal interpretation, controller-specific export and simulation.
- [ ] Identify firmware, fake transport, read-only GRBL telemetry, explicit manual controls and tested streaming.
- [ ] Probing, height compensation, tool change, supervised dry run.
- [ ] First complete PWM 555 V2 fabrication and electrical verification (v0.1 candidate).

All physical and release gates remain pending. See SAFETY.md.
