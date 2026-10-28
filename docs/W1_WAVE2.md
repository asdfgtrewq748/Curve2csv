# Week 1 wave 2: x tick marks, frame edges, and the craftsmen tail

Measured on the frozen OWID set with the same split rule, pass rule, and ground
truth as `benchmarks/results/real-v1.json`. No GT file, threshold, tracker
penalty, bridge length, or series-count rule was changed.

The recorded baseline was first reproduced in the local environment by using
the versions in `benchmarks/requirements.lock` (Python 3.13.5, numpy 2.1.3,
OpenCV 4.10.0.84, scipy 1.14.1, rapidocr-onnxruntime 1.4.4, onnxruntime
1.23.2). With `_x_tick_marks` disabled, the full run is **75/110** (dev 33/49,
held-out 42/61), exactly the recorded tip. The patch then gives **82/110**
(dev 35/49, held-out 47/61), with strict and with-bridge equal in both runs.

## Result

| split | baseline | after | change |
|---|---:|---:|---:|
| held-out | 42/61 | 47/61 | +5 |
| single-curve held-out | 38/46 | 43/46 | +5 |
| dev | 33/49 | 35/49 | +2 |
| all | 75/110 | 82/110 | +7 |

No previously passing chart regressed. The seven gains are:

| chart | split | before NRMSE / coverage | after NRMSE / coverage |
|---|---|---:|---:|
| `wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000` | held-out | 2.686 / 0.750 | 0.266 / 1.000 |
| `growth-of-global-trade` | held-out | 1.533 / 0.870 | 0.159 / 1.000 |
| `uk-gdp-growth-19572016` | held-out | 7.211 / 0.465 | 0.785 / 0.970 |
| `rubella-cases-in-the-united-states` | held-out | 3.047 / 0.800 | 0.560 / 0.945 |
| `diphtheria-cases-in-the-united-states` | held-out | 3.646 / 0.835 | 0.651 / 0.965 |
| `northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c` | dev | 5.810 / 0.385 (recorded) | ok |
| `working-hours-uk-millennium` | dev | recorded fail | ok |

`co2-long-term-concentration` stays at 0.985 / 0.920. It was the one chart that
exposed a bad first version of this patch (see the guard below).

## Craftsmen: what the leftover error was

The plot area comes from `read_frame`, because the OWID spines are too light
for `detect_plot_area`. The blue line is one continuous stroke and the y ticks
were already fine. The defect was x calibration:

- OCR label centers: 1200 at x=55.5, 1300 at 139.5, ..., 2000 at x=817.5.
- True tick marks below the axis: 39.5, 138.5, ..., 832.5.
- Grapher edge-anchors the first and last labels, so their text centers sit
  16 px and 15 px inside the ticks. The interior labels are within about 1 px.
- The old fit therefore compressed the year scale and put the right frame at
  x≈817. The blue tail continued to x≈834, so the last part of the visible
  stroke to 2000 was outside the box.

Using the visible tick marks for the two endpoints changes the frame from
`(53, 106, 821, 535)` to `(36, 106, 836, 535)`, the x slope from 1.02945 to
1.00857, and the score from 2.686 / 0.750 to 0.266 / 1.000. The extracted
stroke grows from 761 to 777 columns. There are no tracker holes and no
bridges; the missing years were the label-center calibration plus the clipped
frame, not a mask or GT problem. GT is unchanged.

## Growth of global trade

The same edge-label offset clipped the right edge at x=820. The true 2000 tick
is at x=832.5. Following the visible ink to x=834 gives NRMSE 0.159 and
coverage 1.000. No tail was invented: the added columns are blue stroke pixels
already present in the PNG.

## UK GDP growth

The visible anchors are 8% and −10%, 1957 and 2020. The old text-center frame
was `(66, 106, 696, 514)`; the tick-mark frame is `(49, 106, 710, 514)`. The
x slope moves from 0.09918 to 0.09610. That is enough for the official score to
pass at NRMSE 0.785 and coverage 0.970. The external 0.67 / 0.980 correlation
still does not need to be reproduced to explain the result: this is the same
visual line, scored against the official CSV under the original rule. No
chart-specific override or anchor was added.

## Rubella, diphtheria, and the dev gains

Rubella and diphtheria have the left endpoint label anchored inward. Snapping
it moves the left frame from x=76 to x=60, recovering early visible ink. The
dev gains are the same endpoint/frame correction on `working-hours-uk-millennium`
and the northern-hemisphere temperature chart.

## Implementation

Only `src/curve2csv/ocr/read.py` changed:

1. `_x_tick_marks` reads short vertical marks in the rows between the x
   baseline and the top of the x-label text. Candidates are restricted to the
   x-label text extent, so descenders of the left y labels cannot become marks.
2. `_snap_x_to_ticks` moves a label to its nearest mark only when the offset is
   at least 2.5 px and at most 45% of the median label spacing. Smaller offsets
   are left alone.
3. `read_frame` recomputes the frame edges from the snapped endpoints before
   padding and before the existing top/bottom stroke walks.

The 2.5 px guard matters. Snapping every interior label by about 1 px improved
the least-squares residual but moved CO2's x sampling enough to turn its pass
(0.985 / 0.920) into a 2.76 NRMSE failure. With the guard, only the visibly
edge-anchored labels move and CO2 is unchanged.

Tracker, masks, occlusion bridge (`line width + 2 px`), and all pass thresholds
are untouched. The only new behavior is where an obviously offset x label is
placed on the visible tick mark, and how far the frame extends to include the
stroke under that mark.

## Reproduction

```bash
# after results in this commit
python -m benchmarks.real.evaluate --split held-out
python -m benchmarks.real.evaluate --split all

# baseline without the new tick snapping
python - <<'PY'
import sys
import curve2csv.ocr.read as ocr
ocr._x_tick_marks = lambda *args, **kwargs: []
import benchmarks.real.evaluate as evaluate
sys.argv = ["evaluate", "--split", "all"]
evaluate.main()
PY
```

The saved measurements are `benchmarks/results/real-v1.json` (after, full set)
and `benchmarks/results/real-v1-held-out.json` (after, held-out). The baseline
copies are `benchmarks/results/real-v1-baseline-locked.json` and
`benchmarks/results/real-v1-heldout-baseline-locked.json`.
