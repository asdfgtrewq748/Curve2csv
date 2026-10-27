# curve2csv 路线图（ROADMAP）

> 状态：规划草案（2026-10-25）。本文所有数值阈值均为 **待验证目标（target, to be validated）**，不是对现有能力的声明。每个阈值在对应里程碑首次跑出基准后可以调整，但调整必须写进 `CHANGELOG.md` 和 PR 说明，并附上调整理由及原始测量值。

## 0. 全局原则

1. **宁缺不编（abstain over fabricate）**：看不清、分不开、校不准的区域输出为空，并打上 `flag`（`occluded` / `ambiguous_color` / `low_confidence` / `out_of_plot` 等），**禁止插值补点**。插值或重采样结果只能作为 `derived` 产物另存，默认不生成。
2. **每次输出必带 QA**：overlay 图（提取点画回原图）、`confidence`、`coverage` 指标、`calibration` 残差，四项缺一视为输出不完整。
3. **门禁顺序**：M(n) 的测试全部通过、基准数字写入 `benchmarks/results/M(n).json` 并在 PR 中公布，之后才能开 M(n+1)。
4. **只用实测数字对外宣传**：README、宣传材料里出现的每一个数字都必须能追溯到某一次基准运行（commit SHA + 数据集版本 + seed）。
5. **原图像素契约**：所有测量都在原始分辨率上完成；缩略图和预览图不能作为校准来源。
6. **版本**：遵循 semver。M1–M4 期间版本号为 `0.x`，M5 发布 `1.0.0`（前提是 API 冻结的判定通过）。

术语和指标定义见 `BENCHMARK.md` §5。下文 `synth-test` 指合成基准集的测试切分，`real-dev` 指真实论文样例集。

---

## M1 — 核心管线 + 合成基准集（`v0.1.0`）

### 范围
- 合成基准生成器（matplotlib，可复现，带 ground truth）：本阶段覆盖线性轴、单曲线或多曲线（颜色可区分）、散点、简单柱状图，以及基础退化（JPEG、噪声、模糊、小角度旋转）。
- 核心管线：图像加载 → 绘图区检测 → 坐标轴/刻度线检测 → **校准（M1 由调用方提供刻度值，或从生成器 sidecar 读取，不做 OCR）** → 前景/网格/文字掩膜 → 按颜色聚类分离系列 → 曲线追踪 → 散点检测 → 柱检测 → 置信度与 flag → 导出 CSV/JSON → overlay QA。
- 基准评测器 `curve2csv-bench`，以及 CI 回归门禁。
- 项目骨架：`pyproject.toml`（MIT，Python ≥3.10）、类型标注（`mypy --strict` 覆盖 `src/`）、`ruff`、`pytest`、GitHub Actions。

### 交付物
- `src/curve2csv/` 中的核心模块（见 `ARCHITECTURE.md`）。
- `benchmarks/generator/`、`benchmarks/evaluate.py`、`benchmarks/configs/m1.yaml`。
- `benchmarks/results/M1.json` 以及 Markdown 分类表。
- `tests/` 中的单元测试、golden 测试和 schema 测试。
- `.github/workflows/ci.yml`（lint + type + test + bench-smoke）。
- `README.md` 草稿（中英双语，仅含安装方式和"开发中"说明）、`LICENSE`（MIT）、`CHANGELOG.md`。

### 验收标准（target，待验证）
数据集为 M1 范围内的 `synth-test`，seed 固定，规模见 BENCHMARK §4。校准使用 sidecar 中给出的刻度真值像素位置加数值，以此把"OCR 误差"与"提取误差"分开评测。

| 指标 | 阈值（pass 条件） | 子集 |
|---|---|---|
| `plot_area_iou` 中位数 | ≥ 0.95 | 全部 |
| `axis_calib_rel_err` 中位数 | ≤ 0.5 % 轴量程 | 全部 |
| `curve_nrmse_range` 中位数 | ≤ 1.0 % 轴量程 | 线图，clean |
| `curve_nrmse_range` P90 | ≤ 3.0 % | 线图，clean |
| `curve_nrmse_range` 中位数 | ≤ 2.0 % | 线图，degraded-light |
| `x_coverage` 中位数 | ≥ 0.90 | 线图，clean，无遮挡 |
| `false_point_rate` 中位数 | ≤ 2 % | 线图，全部 |
| `series_match_acc`（Hungarian） | ≥ 0.95 | 多曲线，颜色可区分，≤4 条 |
| `scatter_f1@3px` 中位数 | ≥ 0.90 | 散点，标记不重叠 |
| `bar_rel_err` 中位数 | ≤ 1.0 % 轴量程 | 柱状图 |
| `flag_precision`（被 flag 的点中真误差 > τ 的比例） | 报告即可，不设门槛 | 全部 |
| 输出完整性（CSV+JSON+overlay+metrics 齐全且通过 schema） | 100 % | 全部 |
| 单图处理时间（CPU，≤ 1600×1200） | 中位数 ≤ 3 s | 全部 |
| 测试 | `pytest` 全绿；`src/` 行覆盖率 ≥ 80 % | — |
| 可复现 | 同一 seed 两次生成，数据集 SHA256 一致 | — |

**硬失败条件**：只要有一张图在被判为"不可见"的 x 区间内输出了无 flag 的点（即编造），M1 就不通过。具体由 `fabrication_count` 统计，必须等于 0。定义见 BENCHMARK §5.6。

### 明确不在范围内
OCR 自动读刻度、对数轴、灰度/线型分离、图例解析、PDF 输入、CLI 的完整功能（只保留最小入口 `python -m curve2csv` 供调试）、Web UI、真实论文样例的门禁（M1 只收集，不设门槛）。

---

## M2 — OCR 自动校准 + 多曲线分离（`v0.2.0`）

### 范围
- 刻度标签 OCR：负号、小数、科学计数法 `1e-3` / `10^{-3}` / `×10³`、千分位。
- 自动校准：刻度线与 OCR 文本配对，用 RANSAC 拟合线性轴或 log10 轴，**自动判断轴类型**，检测倒轴，并输出残差。
- 多曲线分离：颜色（Lab 空间聚类）、**灰度加线型**（实线/虚线/点线/点划线，基于连通段的周期性特征）、标记形状。处理交叉曲线时做连续性约束。
- 图例检测与掩膜（必选），图例文字到系列名的映射（尽力而为，失败时回退为 `series_0..n`）。
- 置信度校准：flag 与实际误差的对应关系必须达标。

### 交付物
`ocr/` 后端抽象（默认实现加至少一个备选）、`calibrate/auto.py`、`separate/linestyle.py`、`legend.py`，`benchmarks/configs/m2.yaml`（扩展到全部参数空间），`benchmarks/results/M2.json`，以及首版 `real-dev` 报告（≥ 20 张真实图，见 BENCHMARK §7）。

### 验收标准（target，待验证）
| 指标 | 阈值 | 子集 |
|---|---|---|
| `tick_ocr_acc`（刻度数值完全正确的比例） | ≥ 0.95 | synth-test 全部 |
| `axis_type_acc`（linear/log 判别） | ≥ 0.98 | 含 log 轴子集 |
| `axis_calib_rel_err` 中位数（全自动） | ≤ 1.0 %（线性）/ ≤ 0.02 decade（log） | synth-test |
| `calib_success_rate`（自动校准未弃权且误差 ≤ 2 %） | ≥ 0.90 | synth-test |
| 校准弃权的正确性 | 误差 > 5 % 却未弃权的比例 ≤ 1 % | synth-test |
| `curve_nrmse_range` 中位数（全自动，端到端） | ≤ 2.0 % | 线图，全部退化 |
| `series_match_acc` | ≥ 0.90 | 多曲线 2–6 条，颜色 |
| `series_match_acc` | ≥ 0.80 | 灰度 + 线型，2–4 条 |
| `scatter_f1@3px` 中位数 | ≥ 0.85 | 散点，含不同标记 |
| `flag_auroc`（点级 flag/confidence 对"误差 > τ"的 AUROC） | ≥ 0.80 | synth-test |
| `fabrication_count` | = 0 | synth-test |
| real-dev（≥ 20 张） | 只报告不设门槛；如 `curve_nrmse_range` 中位数 > 5 %，需写分析 | real-dev |
| 回归 | M1 子集上各指标退化幅度 ≤ 10 %（相对值） | M1 子集 |

### 明确不在范围内
CLI 与批处理的完善、PDF、Web UI、3D 图、极坐标、三元图、等高线/热图、双 Y 轴的自动关联（M2 只检测双 Y 轴并 flag `dual_y_unsupported`）、手写图。

---

## M2.5 — 学习像素分割（可选提取器）

规则分离仍是默认。`extractor=learned` 时用一个小的全分辨率扩张卷积（ONNX，CPU）输出墨迹分数和颜色嵌入，再聚成系列掩膜。训练只用 `benchmarks/learned/` 里的合成图（种子 20261025），不用任何 OWID 图像或 CSV。阈值和 tau 只在合成验证集上选定。held-out 只做评测。

掩膜转点沿用现有校准、OCR 和曲线采样。空隙保持空白，不插值。权重校验失败或没有 onnxruntime 时退回规则路径。Android 没有 onnxruntime 轮子，继续走规则路径。Windows 安装包带上 `segmenter.onnx`。CI 不训练。

---

## M3 — CLI / Python API / 批处理 / PDF（`v0.3.0`）

### 范围
- CLI：`curve2csv extract IMG|PDF [--page N] [--out DIR] [--axes axes.json] [--colors colors.json] [--format csv,json] [--jobs N]`，`curve2csv bench`，`curve2csv inspect`（只生成检测可视化）。
- 稳定的 Python API：`curve2csv.extract(...) -> ExtractionResult`。公开 API 写入 `docs/api.md` 并标注稳定性等级。
- 批处理：目录或 glob 输入、并行执行、断点续跑（按输入 SHA256 跳过已完成项）、汇总 `batch_report.csv`。
- PDF：PyMuPDF 渲染（默认 300 dpi，可配置）；页面内多 figure 检测；优先提取 PDF 内嵌的矢量路径（若可行，作为高置信路径），否则回退到栅格。
- **手动修正入口**：`axes.json`（指定刻度像素和数值、轴类型、倒轴）、`colors.json`（指定或排除系列颜色）、ROI 框，均可覆盖自动结果。被覆盖的部分在输出中标记 `source=manual`。
- 多面板（subplot）切分。

### 交付物
`cli.py`、`api.py`、`batch.py`、`io/pdf.py`、`overrides.py`，`benchmarks/configs/m3.yaml`（含"合成 PDF"子集：把合成图嵌入 A4 双栏版式，同时有矢量和栅格两种形式），以及 `benchmarks/results/M3.json`。

### 验收标准（target，待验证）
| 指标 | 阈值 |
|---|---|
| `figure_detect_recall`（合成 PDF 页内 figure，IoU ≥ 0.8） | ≥ 0.95 |
| `panel_split_acc`（多面板） | ≥ 0.90 |
| PDF 栅格路径端到端 `curve_nrmse_range` 中位数 | 与同参数 PNG 相比差值 ≤ 0.5 个百分点 |
| 矢量路径（可用时）`curve_nrmse_range` 中位数 | ≤ 0.3 % |
| 批处理 500 张：无崩溃，单图失败被隔离并写入报告 | 100 % |
| 断点续跑：中途 kill 后重跑结果一致（逐字节比较 CSV） | 通过 |
| 手动覆盖：提供 `axes.json` 后，校准误差 = 用户给定误差（误差 ≤ 0.1 %） | 通过 |
| CLI 集成测试（subprocess），覆盖所有子命令和错误码 | 全绿 |
| API 文档字符串覆盖率（公开符号） | 100 % |
| M2 指标回归 | ≤ 10 % 相对退化 |
| real-dev（≥ 40 张，含 PDF 页） | 报告；与 WPD 人工真值比较的 `curve_nrmse_range` 中位数目标 ≤ 3 % |

### 明确不在范围内
Web UI、扫描版老论文的 OCR 版面分析（只支持 figure 框检测）、付费墙 PDF 的下载、PDF 文本/表格抽取。

---

## M4 — Web UI 与部署（`v0.4.0`）

### 范围
- Gradio 应用 `app/`：上传图片或 PDF（选页），一键提取；页面展示 overlay、每条系列的表格、置信度和 flag 高亮，并可下载 CSV/JSON/ZIP。
- 交互修正：点选 4 个刻度点并输入数值（类似 WPD）、取色或排除颜色、画 ROI，然后重跑。修正结果可导出为 `axes.json` / `colors.json`，与 CLI 互通。
- 部署：Hugging Face Spaces（CPU basic），Docker 镜像（GHCR）。CI 自动部署 tag 版本。
- 隐私：默认不持久化上传内容，在页面上明确说明。

### 交付物
`app/app.py`、`app/requirements.txt`、`Dockerfile`、`.github/workflows/deploy-space.yml`、UI 端到端测试（`gradio_client` 脚本化调用）。

### 验收标准（target，待验证）
| 指标 | 阈值 |
|---|---|
| Space 冷启动到可用 | ≤ 90 s |
| 单图（≤ 2 MP）端到端延迟，HF CPU basic | 中位数 ≤ 10 s，P95 ≤ 25 s |
| UI 输出与 CLI 输出一致性（同输入同参数） | CSV 逐字节一致 |
| `gradio_client` E2E：上传 → 提取 → 修正轴 → 重跑 → 下载 | 全绿 |
| 上传大小与页数限制、异常图片（非图表/空白/超大） | 返回友好错误，不出现 500 |
| 可用性小测：首个用户（采矿 PhD）用 5 张自己的图完成提取 | 不看文档即可完成；记录每张耗时并与 WPD 人工耗时对比（只报告，不设门槛） |
| M3 指标回归 | ≤ 10 % |

### 明确不在范围内
用户账号、云端存储、付费功能、GPU 推理、移动端适配优化、多语言 UI（只做中英两种文案）。

---

## M5 — 文档、演示、PyPI 发布、宣传材料（`v1.0.0`）

### 范围
- 中英双语 README（安装、30 秒上手、输出格式、可靠性说明、局限、基准表、引用方式）。
- `docs/`（MkDocs）：教程，以及面向 WPD 用户的迁移指南（"WPD 手扒 vs curve2csv"）、输出 schema、FAQ、局限清单。
- 演示 GIF（≤ 8 MB，≤ 30 s）：一张采矿论文风格的支承压力曲线图（使用合成图或已获授权的图）→ CLI 提取 → overlay。
- PyPI 发布：通过 Trusted Publishing（OIDC），`sdist` 和 `wheel`；TestPyPI 先行。
- 宣传材料：项目简介（中英）、一页式基准摘要、可能的投稿或博客草稿。**所有数字都来自 `benchmarks/results/M5.json`**。
- `CITATION.cff`、`CONTRIBUTING.md`、`CODE_OF_CONDUCT.md`、issue 模板（含"提交失败样例"模板）。

### 验收标准（target，待验证）
| 项 | 阈值 |
|---|---|
| 在干净环境里 `pip install curve2csv` 后执行 `curve2csv extract demo.png`（Linux/macOS/Windows，Py 3.10–3.13） | CI 矩阵全绿 |
| TestPyPI → PyPI 发布流程 | 一次成功；版本与 tag 一致 |
| README 中的每个数字 | 都能追溯到 `M5.json`（由脚本 `scripts/check_claims.py` 校验） |
| 文档中的示例代码 | 作为 doctest 或 CI 中的 smoke 测试全部可运行 |
| 完整基准 `synth-test` 与 `real-dev`（≥ 60 张） | 发布完整分类表；M2 至 M4 的所有门禁仍然成立 |
| 1.0 API 冻结 | 公开 API 列表与 `docs/api.md` 一致；后续 breaking change 必须走 major 版本 |

### 明确不在范围内
新算法功能（全部推迟到 1.x）、任何未经实测的性能声明、与商业工具的对比宣传（除非双方使用同一数据集实测）。

---

## 风险与缓解
| 风险 | 缓解 |
|---|---|
| 合成数据太"干净"，与真实论文差距大 | 加入"论文截图"退化模拟；从 M2 起持续扩充 real-dev，并单独报告 real-dev 指标 |
| OCR 依赖太重（PaddleOCR） | 后端可插拔，默认用轻量方案，重依赖作为 `extras` 可选安装 |
| 灰度线型分离难度高 | M2 允许低于彩色子集的阈值；分不开就 flag `ambiguous_series`，不强行分配 |
| HF Spaces CPU 太慢 | 限制输入尺寸；提供本地 Docker |
| 真实样例版权 | 只收 OA（CC-BY 等）或作者授权的图，见 BENCHMARK §7 |
