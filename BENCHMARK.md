# curve2csv 基准设计（BENCHMARK）

> 状态：设计草案（2026-10-25）。本文给出的阈值均为 **target（待验证）**，以 `ROADMAP.md` 为准。**对外宣传只使用实测数字**：README、文档、宣传材料中的每个数字都必须对应 `benchmarks/results/*.json` 里某次运行的记录，记录需包含 commit SHA、数据集版本、seed 和运行环境。

## 1. 目标
1. 用 **已知真值** 的合成图，把误差按来源拆开：检测、校准、OCR、分离、追踪。
2. 用 **分类别报告** 暴露弱项，避免平均数掩盖问题。
3. 用 **CI 回归门禁** 防止性能悄悄退化。
4. 检验 **置信度是否诚实**：flag 掉的区域是否确实是高误差区域，以及有没有出现无 flag 的编造点。

## 2. 生成器（`benchmarks/generator/`）

### 2.1 基本机制
- 基于 matplotlib（Agg 后端），版本锁定在 `benchmarks/requirements.lock`，字体随仓库打包（`benchmarks/fonts/`，均为开源许可字体：DejaVu、Liberation、Noto Sans/Serif CJK、STIX）。避免系统字体差异影响可复现性。
- 每个样本由一个 `SampleSpec`（dataclass，可 JSON 序列化）完全决定，`spec_seed = hash(global_seed, split, index)`。
- 渲染时通过 `ax.transData` 记录 **真值像素坐标**。每个样本输出以下文件：
  - `img.png`（或 `img.jpg`，取决于退化）：退化后的最终图像；
  - `clean.png`：未退化版本（用于调试）；
  - `gt.json`：轴信息（类型、范围、倒轴、刻度值及其像素位置）、绘图区 bbox（像素）、每个系列的数据（数据单位）、稠密采样的像素折线、可见性掩膜（标记哪些 x 区间被图例、文字或其他曲线遮挡）、散点中心坐标、柱的顶边、几何变换矩阵（旋转/裁剪/缩放后的像素映射）。
  - `spec.json`：完整参数。
- **退化后的真值同步变换**：所有几何退化（旋转、透视、裁剪、缩放）都用同一个 3×3 矩阵作用于 GT 像素坐标。
- **可见性真值**：对每个系列单独渲染一张掩膜，再与"其他所有元素"的掩膜求差，得到逐 x 的 `visible` 区间。该区间用于计算 `x_coverage` 和 `fabrication_count`。

### 2.2 数据形状库（贴近首个用户的领域）
| 形状 | 说明 | 典型领域 |
|---|---|---|
| `abutment_pressure` | 超前支承压力：x 为距煤壁距离，峰值 1.5–4 倍原岩应力，之后衰减到 1 | 矿压 |
| `support_load_cycle` | 支架工作阻力随推进距离呈周期性来压（锯齿或尖峰，周期 10–30 m） | 矿压 |
| `stress_strain` | 弹性段 → 屈服 → 峰值 → 软化/残余，可能有多围压族 | 岩石力学 |
| `displacement_scatter` | 带噪声的单调趋势散点，可多组 | 监测 |
| `log_permeability` | y 为 log 轴，跨 2–6 个 decade | 渗透率 |
| `psd_curve` | x 为 log 轴的累计粒径分布（S 形） | 粒度 |
| `generic_smooth` / `generic_noisy` / `step` / `peaks` | 通用形状 | 通用 |

### 2.3 参数空间
| 维度 | 取值 | 引入里程碑 |
|---|---|---|
| `chart_type` | `line`, `line+marker`, `scatter`, `bar`, `grouped_bar` | M1（grouped_bar 为 M2） |
| `n_series` | 1, 2, 3, 4, 6 | M1: 1–4；M2: 1–6 |
| `x_scale` / `y_scale` | `linear`, `log`（log 的范围为 1–6 decade） | log 在 M2 引入 |
| `axis_inverted` | 否 / x 倒 / y 倒（例如"距煤壁距离"向左增大） | M2 |
| `color_mode` | `tab10`、`viridis` 采样、相近色对（ΔE00 在 10–20）、`grayscale`、`black_only` | 灰度在 M2 引入 |
| `line_style` | `-`, `--`, `:`, `-.`，线宽 0.5–3 pt | 非实线在 M2 引入 |
| `marker` | none, `o`, `s`, `^`, `x`, `+`, `D`, `*`；大小 3–10 pt；空心/实心 | M1 |
| `grid` | none / major / major+minor；网格颜色和透明度可变 | M1 |
| `legend` | none / inside（多种位置，可能遮挡曲线）/ outside | M1 |
| `font` | DejaVu Sans、Liberation Serif（Times 类）、STIX、Noto CJK（中文轴标题，例如"支承压力/MPa"）；字号 6–14 pt | CJK 在 M2 引入 |
| `tick_format` | 纯数字、小数、负数、`1e3` 科学计数、`10^n` mathtext、千分位 | M2 |
| `dpi` | 72, 100, 150, 200, 300 | M1 |
| `figure_size` | 3–8 in 宽，宽高比 0.5–1.2 | M1 |
| `crossings` | 曲线是否交叉、局部重合 | M1（只做标注统计）/ M2 |
| `annotations` | 文本标注、箭头、阴影区域（例如"来压区"） | M2 |
| `jpeg_quality` | none, 95, 75, 50, 30 | M1 |
| `noise` | 高斯噪声 σ ∈ {0, 2, 5, 10}/255；椒盐噪声 | M1 |
| `blur` | 高斯 σ ∈ {0, 0.5, 1.0, 1.5} px | M1 |
| `rotation` | 0, ±0.5°, ±1°, ±2° | M1 |
| `paper_screenshot`（M2） | 组合退化：缩放到 0.5–0.8 再放大；屏幕抗锯齿；扫描黄底与纸纹；轻微透视（≤ 1.5°）；周边带论文正文和 caption 的裁剪；色彩空间偏移（sRGB→CMYK→sRGB）；二次 JPEG；摩尔纹 | M2 |
| `pdf_embed`（M3） | 把图嵌入 A4 双栏版式 PDF，分矢量和栅格两种版本，以及多面板 (a)(b)(c) | M3 |

### 2.4 退化强度分档
- `clean`：无退化。
- `light`：jpeg ≥ 75，σ_noise ≤ 2，blur ≤ 0.5，|rot| ≤ 0.5°。
- `medium`：jpeg 50–75，σ_noise ≤ 5，blur ≤ 1.0，|rot| ≤ 1°。
- `heavy`：jpeg 30，σ_noise 10，blur 1.5，|rot| 2°，外加 `paper_screenshot`。

## 3. 种子与可复现
- `GLOBAL_SEED = 20261025`。每个切分有独立的派生种子：`train=1`, `dev=2`, `test=3`。`test` 切分禁止用于调参。
- 生成器使用 `numpy.random.Generator(PCG64)`，禁止使用全局 `np.random`。
- `benchmarks/manifest/{version}.json` 记录每个样本的 SHA256。CI 校验时重新生成 smoke 子集，比对哈希。
- 数据集版本号 `synth-vX.Y`：参数空间变化时升 Y，生成器逻辑变化时升 X。基准结果必须注明数据集版本。

## 4. 切分与规模
| 切分 | 规模（每个里程碑的配置） | 用途 |
|---|---|---|
| `synth-train` | 5,000（可选，仅当后续引入学习组件时使用） | 训练或参数搜索 |
| `synth-dev` | 1,000 | 调参、误差分析 |
| `synth-test` | 2,000（按类别分层，每个主类别 ≥ 100） | 里程碑验收，**冻结** |
| `synth-smoke` | 60（从 test 的分布中抽取，独立种子） | CI，每个 PR 都跑，≤ 5 min |
| `real-dev` | M2 ≥ 20，M3 ≥ 40，M5 ≥ 60 | 真实论文样例，只做报告（见 §7） |
| `real-test` | 冻结的一部分 real 样例（≥ 20），M5 起报告 | 防止对 real-dev 过拟合 |

数据集不进 git（只提交生成器和 manifest）。CI 现场生成 smoke 子集；完整 test 集通过 GitHub Release 资产缓存。

## 5. 指标定义
记号：轴量程 `R_y = y_max - y_min`（线性轴），log 轴在 log10 空间计算，单位为 decade。

### 5.1 检测与校准
- `plot_area_iou`：预测的绘图区 bbox 与 GT bbox 的 IoU。
- `axis_calib_rel_err`：在绘图区内均匀取 11×11 个网格点，分别用预测映射和 GT 映射把像素转成数据值，取 `max |Δ| / R`（线性轴）或 `max |Δlog10|`（log 轴，单位 decade）。x、y 轴分别报告，并报告二者的最大值。
- `axis_type_acc`：linear/log 和倒轴判别的准确率。
- `tick_ocr_acc`：OCR 得到的刻度数值与 GT 完全相等（相对容差 1e-9）的比例。
- `calib_success_rate`：未弃权且 `axis_calib_rel_err ≤ 2 %` 的比例。另报告 `calib_abstain_rate` 和 `calib_silent_fail_rate`（未弃权但误差 > 5 %）。

### 5.2 曲线（线图）
对每个匹配上的系列对（见 5.4）：
- 在 GT 系列 **可见** 的 x 区间上，取 `N = 200` 个均匀 x 采样点。在每个 x 处取预测点中 x 最近的一个，且 |Δx| ≤ 1 px 对应的数据量。若该处无预测点，计为缺失，不计入误差。
- `curve_rmse_data`：数据单位下的 RMSE。
- `curve_nrmse_range`：`curve_rmse_data / R_y × 100 %`（log 轴则用 decade 误差除以 decade 跨度）。
- `curve_max_err_range`：最大绝对误差，以 % 量程表示（用于发现局部跳线）。
- `x_coverage`：在 GT 可见 x 区间中，存在误差 ≤ τ_cov（默认 2 % 量程）的预测点的比例。
- `false_point_rate`：预测点中，距离任何 GT 系列像素折线都 > 3 px（在原图像素空间计算）的比例。
- 对非单值曲线（例如回滞环）：改用对称 Chamfer 距离（像素和 % 量程），M1 只报告不设门槛。

### 5.3 散点
- 预测点与 GT 点在像素空间做 Hungarian 匹配，匹配成立条件为距离 ≤ `tol`，`tol` ∈ {2, 3, 5} px。
- `scatter_precision@tol`、`scatter_recall@tol`、`scatter_f1@tol`；对匹配上的点计算 `scatter_loc_err_px` 中位数。
- 重叠标记（GT 中心距 < 标记直径）单独报告 recall（`scatter_recall_overlap`）。

### 5.4 系列分离
- 构造代价矩阵 `C[i,j] = curve_nrmse_range(pred_i, gt_j)`（散点则用 1 − F1），用 `scipy.optimize.linear_sum_assignment` 求解。代价 > 10 % 的配对视为未匹配。
- `series_match_acc`：(正确匹配数) / max(#pred, #gt)。
- `series_count_err`：|#pred − #gt|。
- `series_purity`：每个预测系列中属于其匹配 GT 系列的点的比例（检测串线）。
- 若带图例名：`legend_name_acc`。

### 5.5 柱状图
- 按 x 类别对齐（Hungarian 按柱中心 x 匹配），`bar_rel_err = |v_pred − v_gt| / R_y`，报告中位数和 P90，以及 `bar_detect_f1`。

### 5.6 置信度与弃权（诚实性）
- 每个输出点带 `confidence ∈ [0,1]` 和 `flags`。定义点"错误"为与 GT 的误差 > τ（默认 2 % 量程），或者是 false point。
- `flag_auroc`：以 `1 - confidence` 为分数预测"错误"，计算 AUROC。
- `flag_precision` / `flag_recall`：把被 flag（任何非空 flag）当作预测"错误"时的精确率和召回率。
- 可靠性图（reliability diagram）：把 confidence 分成 10 个 bin，统计每个 bin 内的实际正确率，并计算 `ece`（Expected Calibration Error）。
- **区域级检查**：GT 中不可见（被遮挡）的 x 区间应满足"无输出"或"有 flag"。
  - `fabrication_count`：落在 GT 不可见区间内（或绘图区外）、**无 flag**，且 confidence ≥ 0.5 的输出点数。**门槛：0**。
  - `abstain_precision`：输出为空或被 flag 的 x 区间中，真实不可见或误差大的比例（反映是否过度保守）。
- 图级：`image_confidence` 与 `curve_nrmse_range` 的 Spearman ρ，期望为负相关（M2 起报告）。

### 5.7 性能
`runtime_s`（中位数、P95）、`peak_rss_mb`，并注明 CPU 型号。

## 6. 报告格式与 CI 门禁

### 6.1 输出
`curve2csv-bench run --config benchmarks/configs/m1.yaml --split test --out benchmarks/results/` 产出：
- `results/<milestone>.json`：元数据（commit、dataset_version、seed、python/os/cpu、耗时）、`per_sample`（每个样本的全部指标）、`aggregates`（按类别聚合）、`gates`（每条门禁的 pass/fail、阈值、实测值）。
- `results/<milestone>.md`：分类别表格，示例格式如下（数值为占位符，**不是结果**）：

| category | n | plot_area_iou (med) | axis_calib_rel_err % (med) | curve_nrmse_range % (med / P90) | x_coverage (med) | false_point_rate % | series_match_acc | scatter_f1@3px | fabrication_count |
|---|---|---|---|---|---|---|---|---|---|
| line/clean/1-series | — | — | — | — / — | — | — | — | n/a | — |
| line/medium/multi-color | — | … | … | … | … | … | … | n/a | … |
| scatter/light | — | … | … | n/a | n/a | … | … | … | … |
| bar/clean | — | … | … | n/a | n/a | n/a | n/a | n/a | … |

  分类维度：`chart_type × degradation_level × series_bucket(1 / 2–3 / 4+) × color_mode × scale`，以及 `domain_shape`。同时给出最差的 20 个样本列表，每个样本附 overlay 缩略图路径。
- `results/<milestone>_failures/`：最差样本的 overlay 图和 GT 对照图。

### 6.2 CI 回归门禁
- **每个 PR**：在 `synth-smoke` 上跑全部指标。①里程碑门禁的硬项（例如 `fabrication_count = 0`、输出完整性 100 %）不能违反；②与 `main` 上的基线 `benchmarks/baseline/smoke.json` 比较，任一核心指标（`curve_nrmse_range` 中位数、`x_coverage`、`series_match_acc`、`scatter_f1@3px`、`axis_calib_rel_err`）的相对退化超过 10 %，**或**绝对退化超过该指标阈值余量的 50 %，CI 判定失败。
- **合并到 main 后**：更新 smoke 基线（由 bot 提交，或手动执行 `make update-baseline`，需在 PR 中说明）。
- **里程碑 PR**：额外手动触发（`workflow_dispatch`），或用 `bench-full` 标签触发完整 `synth-test` 运行，并把 `results/M*.md` 贴进 PR 正文。
- 有意改变指标的 PR（例如为提高诚实性而降低 coverage）必须加 `metric-change` 标签，并写明取舍。

## 7. 真实论文样例（`benchmarks/real/`）

### 7.1 收录流程
1. **来源限制**：只收开放获取（CC-BY、CC-BY-SA、CC0 等允许再分发的许可）的论文图，或作者、首个用户书面授权的图。**不收付费墙内容**，不收许可不明的截图。
2. 每个样例一个目录：`real/<id>/`
   - `img.png`：原始分辨率（来自 PDF 时注明渲染 dpi，或使用内嵌图原图）。
   - `meta.json`：`doi`、`figure_id`、`panel`、`license`、`license_url`、`source_url`、`chart_type`、`axis_types`、`n_series`、`domain`（`mining_pressure` / `stress_strain` / `displacement` / `permeability_log` / `psd_log` / …）、`added_by`、`date`。
   - `gt_wpd.json` 和 `gt.csv`：**用 WebPlotDigitizer 人工提取的真值**，同时附上 WPD 项目文件（`.tar` 导出）、校准点（每轴 ≥ 2 个已核实的刻度，优先用刻度线交点）和 `wpd_overlay.png`（人工 QA 图）。
   - `visibility.json`（可选）：人工标注的遮挡和不可辨识区间。
3. **真值质量要求**：标注者在 overlay 上确认点落在线上；如果文中有标注值，抽 2–4 个对照；不确定的区间标记为 `uncertain`，这些区间不计入误差评测。
4. 第二人复核（至少 20 % 的样例），报告标注者间 `curve_nrmse_range`，作为 real 集误差的下限参考。
5. 许可不允许再分发时，只提交 `meta.json`、`gt.csv` 和获取脚本（`fetch.py`，从 OA 源下载并裁剪），图像不进仓库。

### 7.2 评测差异
- 真实样例没有像素级 GT 折线，`false_point_rate` 改为相对人工点的近似计算：到人工折线（线性插值，**仅用于评测**）的距离 > 3 px 即算 false point。在报告中注明这一近似。
- real 集只做报告，不进 CI 硬门禁；M5 起 `real-test` 冻结。

### 7.3 首个用户的典型样例清单（征集目标）
支承压力/工作阻力–推进距离曲线、应力–应变全过程曲线（多围压）、位移监测散点、多系列折线（不同工作面或方案）、渗透率 log 轴、粒径分布 log 轴。每类至少 5 张。

## 8. 宣传口径
- 只引用 `results/*.json` 中的实测值，并注明数据集（synth/real）、版本、切分和 commit。
- 合成集与真实集的结果分开呈现，**不得用合成集数字代表真实论文表现**。
- 局限（失败类别、弃权率）与优点一起列出。`scripts/check_claims.py` 会扫描 README 和文档中的数字，与结果文件比对。

## 9. v1 真实图（`owid-grapher-v1`）

来源是 Our World in Data 的 grapher 导出，不是人工描点。收录规则在评分之前定死，不看提取是否成功：

- 图类型：grapher 的第一个 `chartTypes` 是 `LineChart` 或 `ScatterPlot`。没有该字段时，SVG 里不能出现 `Areas` 或 `Bars`。堆叠面积和条形图不进入集合。
- 输入图像：该图的 PNG（出版页面上的栅格）。
- 系列真值：同页 CSV，只保留图上 `selectedEntityNames` 的 1–6 条系列（与提取器 `max_series` 相同），并且年份和数值落在 SVG 刻度范围内。1–3 条在目录抽样里大约只占三分之一，凑不满 100 张，所以上限在评分前改成 6。
- 轴范围和 linear/log：同页 SVG 里 `<text>` 的刻度文字和坐标。这与 PNG 上的 OCR 无关。log 轴在 log10 空间算误差。
- 许可：CC BY 4.0（https://creativecommons.org/licenses/by/4.0/）。PNG 可以再分发，放在 `benchmarks/real/figures/`。每张图的 URL 记在 `benchmarks/real/gt/<slug>.json`。

切分在评分之前冻结：`int(sha256(slug).hexdigest(), 16) % 5 < 2` 为 dev，其余为 held-out。改提取器只看 dev。

一张图算正确，当且仅当下面三条同时成立：

1. 去掉 flag 或空坐标之后仍有点的预测系列数，等于真值系列数。
2. 用 NRMSE 做 Hungarian 配对后，每个系列的 `curve_nrmse_range ≤ 2`（占轴量程的百分比）。
3. 每个系列的 `x_coverage ≥ 0.90`。

x 方向在真值系列自己的 x 范围内均匀取 200 个点。某点算对齐，当最近的预测点与它的 x 距离不超过 1 个像素（像素宽度用 SVG 两端刻度的跨度）。NRMSE 只在对齐的点上计算，缺失点不进入误差。`x_coverage` 是这些采样点里、y 误差也 ≤ 2% 量程的比例。flag 或空坐标的点在评分前删除，所以它们降低 coverage，不记成误差。

直线参数误差：真值在轴空间里线性拟合 R² ≥ 0.98 时，报告斜率相对误差和截距占 y 量程的比例。它不是通过条件。实测写在 `benchmarks/results/real-v1.json`，按 dev、held-out、全体分开。

同一规则下的实测（Python 3.12.3）：修正前 held-out 27/61（44.3%）、全体 52/110（47.3%）；修正绘图框和陡段之后 held-out 38/61（62.3%）、全体 69/110（62.7%）。把同一笔画的抗锯齿色边并回该笔画之后，held-out 39/61（63.9%）、全体 70/110（63.6%），dev 仍是 31/49（63.3%）。90% 目标未达到。held-out 剩余失败是 x_coverage 8、nrmse_and_coverage 7、series_count 4。`global-smallpox-cases`、`diphtheria-cases-in-the-united-states`、`rubella-cases-in-the-united-states` 的中位有符号误差约为 0，但有一段年份的描线与已发布 CSV 相差数十像素，这些图保持失败，不按 CSV 改几何。smoke 的 `fabrication_count` 仍是 46，硬门禁仍是 0。

去掉落在另一条脊线上、又离自身中心线超过 6px 的渗色像素之后（`df05503`）：dev 32/49（65.3%），held-out 仍是 39/61（63.9%），全体 71/110（64.5%）。90% 目标未达到。新通过的只有 dev 的 `population-unwpp`（第二条系列的 x-coverage 从 0.20 到 0.97）。`06d9965` 上已通过的图全部仍然通过。held-out 失败桶不变：x_coverage 8、nrmse_and_coverage 7、series_count 4、no_calibration 3。全体失败：x_coverage 15、nrmse_and_coverage 13、series_count 6、no_calibration 5。held-out 上覆盖率上升但仍低于 0.90 的有 `annual-fish-catch-taxa`（0.165→0.610）、`breast-cancer-death-rate-in-women`（0.130→0.535）、`maize-production`（0.125→0.485）、`difference-in-female-and-male-life-expectancy-at-age-45`（0.030→0.245）。`cumulative-space-visits` 的覆盖率仍是 0.075，标记之间的空档保持为空。四张描线与已发布 CSV 不一致的图保持失败。dev 的 `stratospheric-ozone-concentration-projections` 预测系列从 3 条变成 4 条（真值 3），原因从 nrmse_and_coverage 变为 series_count，该图在上一版已经失败。同一 60 张 smoke、sidecar 轴、结果未写入 `benchmarks/results/smoke.json`：`fabrication_count` 48（00052 与 00053 各多 1 点，仍是生成器不可见区间里的同色墨迹），`curve_nrmse_range_median` 0.859，`x_coverage_median` 0.811，`series_match_acc` 0.790。硬门禁仍是 0。按列改跟最近脊线的跟踪器把 smoke 的 `x_coverage_median` 从 0.811 降到 0.731，并把 `fabrication_count` 从 48 升到 50，因此留在测量记录里。下一步只做更严的脊线连续性：沿父笔画的颜色走，只在很短的交叉处取消 flag，36px 跳跃上限保持不变。

颜色约束的动态规划跟踪，加上只在另一条系列墨迹遮挡处补的短桥（`e7dc53d`）。缺口不超过线宽加 2 像素，两侧各有至少 16 列本系列支撑，补上的点带 `interpolated=1`。严格评分丢掉这些点，with-bridge 评分把它们算进覆盖率。两套分数相同：dev 32/49（65.3%），held-out 39/61（63.9%），全体 71/110（64.5%）。90% 目标未达到。`df05503` 上已通过的图全部仍然通过，也没有新通过的图。held-out 失败桶不变：x_coverage 8、nrmse_and_coverage 7、series_count 4、no_calibration 3。全体失败：x_coverage 15、nrmse_and_coverage 13、series_count 6、no_calibration 5。110 张图共 59 个桥接点。含 OCR 的平均 CPU 时间 1.026 秒/张，中位 0.959 秒/张。覆盖率上升但仍低于 0.90 的有 dev 的 `stratospheric-chlorine-concentrations`（0.770→0.855）、`cohort-fertility-rate`（0.410→0.645）、`stomach-cancer-death-rate`（0.440→0.605），held-out 的 `breast-cancer-death-rate-in-women`（0.535→0.620）、`maize-production`（0.485→0.585）、`difference-in-female-and-male-life-expectancy-at-age-45`（0.245→0.390）。`cumulative-space-visits` 的覆盖率仍是 0.075。四张描线与已发布 CSV 不一致的图保持失败。同一 60 张 smoke、sidecar 轴、结果未写入 `benchmarks/results/smoke.json`：`fabrication_count` 59（上一版 48），`bridged_count` 92，`curve_nrmse_range_median` 0.859，`x_coverage_median` 0.798，`series_match_acc` 0.813。硬门禁仍是 0。下一步只在两侧斜率一致、且缺口上仍有另一条系列墨迹时把桥加长，补点继续标 `interpolated=1`。

把裂成短段的 1 像素笔画改成折线跟踪之后（`c567941`）：dev、held-out、全体的通过数不变，仍是 32/49、39/61、71/110。`cumulative-space-visits` 的俄罗斯从 31 个散点、覆盖率 0.075 变成折线，覆盖率 0.855，NRMSE 0.139。`land-natural-share` 的德国从覆盖率 0.115、NRMSE 0.21 变成覆盖率 0.725、NRMSE 0.089。两张仍因覆盖率失败。蒙版里没有该系列像素的列保持为空。smoke 与 `e7dc53d` 相同。

单系列刻度（`e5dcdf7`）：`803.719BCE`、`30million` 这类粘连标签可以读出，BCE 标签落在文字外缘。held-out 40/61（65.6%），dev 33/49，全体 73/110。新通过的是 held-out 的 `co2-long-term-concentration`（NRMSE 0.985，覆盖率 0.920）和 dev 的 `foreign-born-population-of-the-united-states`（NRMSE 0.130，覆盖率 1.0）。`nitrous-oxide-long` 现在能标定，仍失败（NRMSE 5.19，覆盖率 0.375）。单系列 held-out 从 35/46 到 36/46。smoke 不变，`fabrication_count` 59。

图框沿笔画向下延伸，并补回左侧漏读的 y 刻度（`8c12888`）：held-out 42/61，全体 75/110，dev 仍是 33/49。新通过的是 `same-sex-marriage-country-count`（NRMSE 0.175，覆盖率 0.990）和 `mention-of-the-word-capitalism-in-new-york-times-articles`（NRMSE 1.163，覆盖率 0.900）。单系列 held-out 38/46。这两张都是算法，GT 未改。smoke 的 `fabrication_count` 仍是 59。
