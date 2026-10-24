# curve2csv 架构（ARCHITECTURE）

> 状态：提案（2026-10-25）。目标：Python ≥ 3.10，MIT 许可，`src/` 布局，全量类型标注。

## 1. 设计原则
1. **阶段化、可替换**：每个阶段是一个纯函数式接口（输入 dataclass，输出 dataclass），便于单测、可视化和手动覆盖。
2. **证据链**：每个输出点都能追溯到原图像素（`px`, `py`）以及产生它的阶段和依据。
3. **弃权优先**：任何阶段都可以返回 `Abstain(reason)`，下游据此输出空值和 flag，而不是继续"猜"。
4. **原图像素契约**：所有几何量以原始输入的像素坐标为准；内部若做缩放或纠偏，需记录变换矩阵并反变换回原图。
5. **重依赖可选**：核心只依赖 numpy、opencv-python-headless、scikit-image、scipy、pillow；OCR、PDF 和 UI 通过 extras 安装。

## 2. 包布局
```
curve2csv/
├── pyproject.toml              # hatchling; extras: [ocr-tesseract], [ocr-paddle], [ocr-easyocr], [pdf], [ui], [bench], [dev]
├── src/curve2csv/
│   ├── __init__.py             # 公开 API: extract, ExtractionResult, __version__
│   ├── api.py                  # extract(image|path, *, overrides=None, config=None) -> ExtractionResult
│   ├── cli.py                  # curve2csv extract|bench|inspect (M1 只做最小 extract)
│   ├── config.py               # PipelineConfig (dataclass, 可从 TOML/YAML 加载)
│   ├── types.py                # 所有公共 dataclass / enum / Flag
│   ├── pipeline.py             # 编排各阶段, 捕获 Abstain, 汇总诊断
│   ├── io/
│   │   ├── image.py            # 加载(含 EXIF 旋转, 透明通道合成白底), 颜色空间
│   │   ├── pdf.py              # [M3] PyMuPDF 渲染 / 矢量路径提取 / figure 裁剪
│   │   └── export.py           # CSV / JSON 写出, schema 版本
│   ├── detect/
│   │   ├── plot_area.py        # 绘图区 bbox: 轴线 Hough/形态学 + 最大矩形框
│   │   ├── axes.py             # 坐标轴线, 刻度线位置, 倒轴线索
│   │   ├── text.py             # 文字区域掩膜 (MSER/形态学; M2 起结合 OCR bbox)
│   │   ├── legend.py           # [M2] 图例框与样本-文字配对
│   │   └── grid.py             # 网格线检测与掩膜
│   ├── ocr/                    # [M2]
│   │   ├── base.py             # OCRBackend Protocol
│   │   ├── tesseract.py, paddle.py, easyocr.py
│   │   └── parse_numbers.py    # "−1.5", "1e-3", "10^{-3}", "×10³", "1,000" → float
│   ├── calibrate/
│   │   ├── model.py            # AxisCalibration: 线性/log10, 倒轴, px<->data
│   │   ├── manual.py           # 来自用户/sidecar 的刻度点
│   │   └── auto.py             # [M2] 刻度线×OCR 配对 + RANSAC + 类型选择(残差/BIC)
│   ├── separate/
│   │   ├── foreground.py       # 前景掩膜 = 非背景 − 轴 − 网格 − 文字 − 图例
│   │   ├── color.py            # Lab 空间聚类 (k 由 BIC/轮廓系数选择, 抗锯齿边缘处理)
│   │   └── linestyle.py        # [M2] 灰度下按虚线周期/线宽/标记形状分离
│   ├── extract/
│   │   ├── curve.py            # 逐列中心线 + 连通性/平滑先验追踪; 交叉处理; 非单值回退
│   │   ├── scatter.py          # 标记检测: 模板/连通域/距离变换+峰值, 重叠拆分
│   │   └── bar.py              # 柱检测: 矩形连通域, 顶边, 基线
│   ├── quality/
│   │   ├── confidence.py       # 点级/系列级/图级置信度
│   │   ├── flags.py            # Flag 规则
│   │   ├── coverage.py         # x_coverage (自评, 基于可见前景)
│   │   └── overlay.py          # QA overlay 渲染
│   └── overrides.py            # [M3] axes.json / colors.json / roi 读取与合并
├── benchmarks/                 # 见 BENCHMARK.md
│   ├── generator/  configs/  evaluate.py  metrics.py  report.py  baseline/  real/
├── app/                        # [M4] Gradio
├── tests/  docs/  scripts/
└── .github/workflows/ci.yml
```

## 3. 管线阶段与接口

### 3.1 核心类型（`types.py`，节选）
```python
from dataclasses import dataclass, field
from enum import Enum, Flag as _Flag
import numpy as np
from numpy.typing import NDArray

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 (原图像素, 右开)

class AxisScale(str, Enum):
    LINEAR = "linear"; LOG10 = "log10"

class PointFlag(_Flag):
    NONE = 0
    LOW_CONFIDENCE = 1      # 综合置信度 < 阈值
    AMBIGUOUS_SERIES = 2    # 归属多个系列都可能 (交叉/相近色)
    NEAR_TEXT = 4           # 邻近文字/图例掩膜
    NEAR_GRID = 8
    EDGE_OF_PLOT = 16
    THICK_SEGMENT = 32      # 垂直方向像素过厚, 中心不确定
    MANUAL = 64             # 来自手动覆盖
    INTERPOLATED = 128      # 仅 derived 产物可出现, 主输出禁止

@dataclass(frozen=True)
class Abstain:
    stage: str
    reason: str             # e.g. "no_axis_found", "ocr_inconsistent", "colors_inseparable"

@dataclass(frozen=True)
class LoadedImage:
    rgb: NDArray[np.uint8]  # HxWx3
    source: str             # 路径/哈希
    sha256: str
    page: int | None = None
    dpi: float | None = None

@dataclass(frozen=True)
class PlotArea:
    bbox: BBox
    x_axis_px: float        # 轴线 y 位置
    y_axis_px: float        # 轴线 x 位置
    score: float

@dataclass(frozen=True)
class Tick:
    axis: str               # "x" | "y"
    px: float               # 沿轴像素坐标
    value: float | None     # M1: sidecar/手动; M2: OCR
    text: str | None = None
    ocr_conf: float | None = None

@dataclass(frozen=True)
class AxisCalibration:
    axis: str
    scale: AxisScale
    a: float; b: float      # data' = a*px + b, data' = value 或 log10(value)
    inverted: bool
    residual_rel: float     # 刻度拟合残差 / 量程
    n_ticks_used: int
    source: str             # "sidecar" | "manual" | "auto"
    def px_to_data(self, px: NDArray[np.float64]) -> NDArray[np.float64]: ...
    def data_to_px(self, v: NDArray[np.float64]) -> NDArray[np.float64]: ...

@dataclass(frozen=True)
class Masks:
    foreground: NDArray[np.bool_]
    text: NDArray[np.bool_]; grid: NDArray[np.bool_]; legend: NDArray[np.bool_]; axes: NDArray[np.bool_]

@dataclass(frozen=True)
class SeriesMask:
    series_id: str
    color_lab: tuple[float, float, float] | None
    style: str | None       # "solid" | "dashed" | ... (M2)
    mask: NDArray[np.bool_]
    separation_score: float # 与最近其他簇的 ΔE00 / 间隔度

@dataclass(frozen=True)
class DataPoint:
    x: float | None; y: float | None   # None = 弃权
    px: float; py: float
    confidence: float
    flags: PointFlag

@dataclass
class Series:
    series_id: str
    kind: str               # "line" | "scatter" | "bar"
    label: str | None
    color_hex: str | None
    points: list[DataPoint]
    gaps: list[tuple[float, float]]    # 数据单位 x 区间: 不可见/弃权
    coverage: float                    # 自评可见覆盖率
    confidence: float

@dataclass
class ExtractionResult:
    schema_version: str     # "1.0"
    source: LoadedImage
    plot_area: PlotArea | Abstain
    calibration: dict[str, AxisCalibration | Abstain]
    series: list[Series]
    image_confidence: float
    abstentions: list[Abstain]
    diagnostics: dict[str, object]     # 各阶段耗时, 簇数选择依据等
    def to_csv(self, path) -> None: ...
    def to_json(self, path) -> None: ...
    def overlay(self, path) -> None: ...
```

### 3.2 阶段接口
| # | 阶段 | 函数签名 | 失败行为 |
|---|---|---|---|
| 1 | 加载 | `load_image(src) -> LoadedImage` | 抛 `InputError` |
| 2 | 绘图区 | `detect_plot_area(img, cfg) -> PlotArea \| Abstain` | 弃权 → 整图无输出 |
| 3 | 轴/刻度 | `detect_ticks(img, area, cfg) -> list[Tick]` | 刻度 < 2 → 校准弃权 |
| 4 | 校准 | `calibrate(ticks, area, overrides) -> dict[axis, AxisCalibration \| Abstain]` | 残差 > `max_calib_residual` 则弃权 |
| 5 | 掩膜 | `build_masks(img, area, cfg) -> Masks` | — |
| 6 | 分离 | `separate_series(img, masks, cfg) -> list[SeriesMask]` | 簇不可分 → 合并为一个簇并打 `AMBIGUOUS_SERIES` 标记 |
| 7 | 提取 | `extract_curve / extract_scatter / extract_bar(series_mask, area, calib, cfg) -> Series` | 局部不可辨 → 出现 gap |
| 8 | 质量 | `score_confidence(series, masks, calib) -> Series`；`image_confidence(...)` | — |
| 9 | 导出 | `to_csv / to_json / overlay` | — |

图类型判别（line/scatter/bar）由阶段 6 和 7 根据簇的形态特征自动完成，也可由 `config.chart_type` 强制指定。

### 3.3 置信度构成（初版启发式，M2 校准）
点级 `confidence = Π` 各项（截断到 [0,1]）：
- 列内像素厚度与线宽估计的比值（过厚说明中心不确定）；
- 到文字、图例、网格掩膜的距离；
- 系列归属的颜色距离间隔（Lab ΔE00 margin）；
- 与追踪平滑先验的偏差；
- 校准残差（同一张图内所有点共享）。

规则：`confidence < cfg.min_point_confidence`（默认 0.3）的点，**主输出中坐标置为空**，但保留 `px` 和 flag。M2 用 dev 集拟合等张回归（isotonic），把启发式分数校准为"误差 ≤ τ 的概率"。

## 4. 输出 schema

### 4.1 CSV（长表，每点一行；`<stem>.csv`）
```
series_id,series_label,kind,x,y,confidence,flags,px,py
s0,,line,12.5,3.41,0.93,,412.0,188.5
s0,,line,13.0,,0.12,LOW_CONFIDENCE|NEAR_TEXT,418.0,190.0
```
- `x`/`y` 为空表示弃权（**不插值**）。`flags` 用 `|` 连接。
- 可选的宽表 `--wide`：按 x 对齐，只在各系列共享 x 网格时可用（例如柱状图），否则拒绝生成。
- 文件头不写注释行（保证与 pandas、Excel 兼容），元数据放在 JSON 中。

### 4.2 JSON（`<stem>.json`，`schema_version: "1.0"`，JSON Schema 文件位于 `src/curve2csv/schema/result.schema.json`）
```json
{
  "schema_version": "1.0",
  "tool": {"name": "curve2csv", "version": "0.1.0", "config_hash": "…"},
  "source": {"path": "fig3.png", "sha256": "…", "page": null, "width": 1600, "height": 1200},
  "data_origin": "digitized_from_figure",
  "disclaimer": "Values digitized from a published figure; not original measurements.",
  "plot_area": {"bbox": [120, 40, 1550, 1100], "score": 0.97},
  "axes": {
    "x": {"scale": "linear", "inverted": false, "a": 0.0123, "b": -1.47, "residual_rel": 0.0008,
           "ticks": [{"px": 120.0, "value": 0, "text": "0", "source": "sidecar"}], "source": "sidecar"},
    "y": {"scale": "log10", "…": "…"}
  },
  "series": [
    {"series_id": "s0", "label": null, "kind": "line", "color_hex": "#1f77b4", "style": "solid",
     "confidence": 0.91, "coverage": 0.96,
     "gaps": [[40.0, 46.5]],
     "points": [{"x": 12.5, "y": 3.41, "px": 412.0, "py": 188.5, "confidence": 0.93, "flags": []}]}
  ],
  "image_confidence": 0.88,
  "abstentions": [{"stage": "legend", "reason": "not_implemented_m1"}],
  "qa": {"overlay": "fig3.overlay.png", "metrics": {"n_points": 812, "n_flagged": 37, "n_abstained": 12}},
  "diagnostics": {"timings_ms": {"plot_area": 21, "…": 0}}
}
```

### 4.3 QA overlay（`<stem>.overlay.png`）
- 以原图为底，降低饱和度并设透明度 60 %。
- 每个系列用高对比色绘制提取点（直径 2–3 px）和折线连接（**只连接相邻且无 gap 的点**）。
- 低置信或被 flag 的点用空心红圈表示；gap 区间在 x 轴下方用红色细条标出。
- 画出绘图区框和校准刻度：标出刻度像素位置与读数，残差过大的刻度用红色标出。
- 右侧或底部的信息栏：系列 id、颜色、coverage、confidence、校准残差、版本号。
- 可选输出 `<stem>.recreated.png`：用提取数据重新绘制的图，与原图并排对比。

## 5. 依赖选择
| 用途 | 选择 | 备选 | 理由与取舍 |
|---|---|---|---|
| 图像处理 | `opencv-python-headless` | — | Hough、形态学、连通域、仿射变换都快而成熟；headless 版本避免 GUI 依赖 |
| 图像算法补充 | `scikit-image` | — | 骨架化、区域属性、Lab/ΔE00 颜色计算、MSER 补充 |
| 优化/匹配 | `scipy` | — | `linear_sum_assignment`、插值（仅评测用）、信号处理 |
| 聚类 | `scikit-learn`（可选，GMM/BIC） | 自实现 k-means | 核心可以不依赖 sklearn；先用 scipy 的 `kmeans2`，需要 GMM 时以 extra 引入 |
| OCR（M2） | 默认 **Tesseract**（`pytesseract`，`--psm 7`，数字白名单） | PaddleOCR、EasyOCR | 见下表 |
| PDF（M3） | **PyMuPDF**（`pymupdf`） | pdfplumber + pypdfium2、pdf2image（poppler） | PyMuPDF 渲染快，且能拿到矢量路径（`page.get_drawings()`）；**注意许可：AGPL-3.0 或商业许可**，因此作为可选 extra `[pdf]` 提供，在 README 中说明。如需纯宽松许可，可用 `pypdfium2`（Apache/BSD）做渲染备选 |
| UI（M4） | Gradio | Streamlit | HF Spaces 原生支持，组件里有图像标注 |
| 基准生成 | matplotlib | — | 真值来自 transData，生态最普遍 |
| 打包 | hatchling + `uv`/pip | setuptools、poetry | 简洁，支持 PEP 621 |
| 质量工具 | ruff、mypy（strict）、pytest、pytest-cov、hypothesis | — | hypothesis 用于数值解析和校准的性质测试 |

### OCR 方案对比
| 方案 | 优点 | 缺点 | 定位 |
|---|---|---|---|
| Tesseract 5 | 系统包轻量、CPU 快、许可宽松（Apache-2.0）；单行数字配合白名单准确率可以 | 小字号、低分辨率、上标指数（`10^-3`）效果差；需要系统安装 `tesseract-ocr` | 默认后端；先对刻度标签做 3–4 倍放大和二值化 |
| PaddleOCR | 对小字、中文、倾斜文本强，检测加识别一体 | 依赖 paddlepaddle，体积大（数百 MB），安装在部分平台上麻烦 | `[ocr-paddle]` 可选，"高精度"模式 |
| EasyOCR | 纯 pip（PyTorch）安装，多语言 | 依赖 PyTorch，首次下载模型；CPU 慢 | `[ocr-easyocr]` 可选 |
| 无 OCR（模板匹配） | 零依赖；合成字体上很准 | 对真实字体泛化差 | 仅作对照基线 |

指数与上标的处理：检测到底数 "10" 加上方小字时，单独裁剪上标区域再识别。所有 OCR 结果都要经过 **一致性检查**：刻度值与像素位置必须单调且等差（线性轴）或等比（log 轴），不一致就剔除离群值或弃权。

## 6. 配置与覆盖
- `PipelineConfig` 中所有阈值都带默认值，`config_hash` 写入输出 JSON。
- 覆盖优先级：`manual overrides > config > auto`。覆盖来源写入 `source` 字段，覆盖产生的点带 `MANUAL` flag。

## 7. 错误处理与日志
- 用户输入错误抛出 `curve2csv.errors.InputError`；算法上不确定的情况一律用 `Abstain` 表示，**不抛异常**。
- 使用 `logging` 记录日志，库代码中不 `print`；CLI 的 `-v/-vv` 控制日志级别。
