# RES-017 — Direct cutout comparison

Status: all five cutout reference cases passed. Original FlatCAM offset_contours and any_cutout_handler run in pinned upstream environment. Contour records supplied explicitly, not a test of outline_contours or Gerber stroke reconstruction. Matched canonical zero-width inputs, radius 0.5 mm, margin 0.002 mm. Five fixtures: rectangle, four tabs, rectangular inner window, concave outline, inaccessible 0.8 mm window. Compare line length, discrete Hausdorff, nominal swept symmetric difference, gap length, independent anchors, inner count and cut/gap partition. FlatCAM uses default buffer resolution (16 segments/quadrant), Studio 64. Preliminary fixture-specific thresholds: length 0.01 mm, discrete Hausdorff 0.002 mm, swept difference 0.02 mm²; no exact equivalence required across different tessellations. For an inaccessible window, expect empty upstream offset and explicit Studio rejection rather than a partial plan. Path component counts may differ due to closed contour seam splitting. No Z, tab strength, clamping, physical machining, full upstream job or real PCB validation. Results verified below. No production code changed.

## Verified results
Commit 674636446068dc508dd842890cc6098643615626: https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45889227136 completed successfully. Research suite 136 tests passed on both OS: https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45889219873.

| Case | Studio exterior cut length mm | FlatCAM exterior cut length mm | Discrete Hausdorff mm | Swept difference mm² |
|---|---:|---:|---:|---:|
| rectangle | 103.154079856 | 103.152892482 | 0.000604681 | 0.001835253 |
| four-tabs | 91.154079856 | 91.152892482 | 0.000604681 | 0.001835253 |
| internal-window | 91.154079856 | 91.152892482 | 0.000604681 | 0.001835253 |
| concave-board | 102.938599820 | 102.937115602 | 0.000604681 | 0.002294066 |

Four gaps totaled 12 mm in both engines; internal window length 15.984 mm in both; discrete Hausdorff for the inner path zero, gap discrepancy at floating point roundoff. FlatCAM returned an empty inner offset for the narrow window, Studio rejected the complete preview. All predeclared thresholds passed without modification. Shared GEOS algorithms and synthetic fixtures limit independence and generalization. Full source reconstruction, real board, multi-tool rest comparison, Z and physical safety remain pending.
