# Training provenance

The segmenter is trained only on charts drawn by `benchmarks/learned/render.py`.
No Our World in Data PNG, CSV, or SVG is read. Held-out figures are evaluation
only. The ink threshold and embedding tau are chosen on the synthetic
validation charts inside the same training run, before any OWID image is opened.

- Seed: `20261025`
- Canvas: 850×600
- Styles: matplotlib, Excel-like, ggplot-like, OWID-like, and muted palettes.
  These are original stand-ins, not copies of the evaluated figures.
- Supervision: per-pixel series ids on visible ink. Legends, gridlines, text,
  and white occluders stay background. JPEG, blur, and noise touch the RGB
  image only, after the label is stored.
- Close colors are a 14–36 RGB nudge. Identical-color series pairs are not
  trained. A local color embedding cannot split two strokes that share a color.
- Weights license: MIT, same as this repository. `src/curve2csv/models/segmenter.onnx`
  is produced by `python -m benchmarks.learned.train` and checked with
  `segmenter.sha256`.
- Libraries: Matplotlib (BSD), the vendored DejaVu font in `benchmarks/fonts/`,
  OpenCV (Apache-2.0) for raster labels, PyTorch (BSD) for training only,
  ONNX opset 17. Inference uses onnxruntime (MIT), already required by the
  `ocr` extra. PyTorch is not a project dependency.
- Android: Chaquopy has no onnxruntime wheel. The on-device app keeps the
  rule-based separator.
- CI does not train. The default extractor remains `rules`.

Completed run (one pass, CPU):

- 80 train charts, 8 validation charts, seed 20261025, 3-channel 256 crops,
  batch 8, Adam learning rate 1e-3, 400 steps.
- 20449 parameters. Best validation soft-dice 0.504 (still rising at the last
  step; this is the checkpoint that was exported).
- Synthetic-val sweep: ink threshold 0.35, embedding tau 0.5, matched dice
  0.352. Those two numbers are the `PipelineConfig` defaults.
- `segmenter.onnx` is 84488 bytes, sha256
  `3e49085c899725a9037549cbc4dbef514567f30d881d23d58880f21c580e98bf`.
