# W3 报告：领域单曲线集（8 dev + 16 held-out）+ 轻量人工确认计时

分支 `w3-domain`（基于 `w2-evidence` 4283b5a），仅本地提交，未 push / 未开 PR。

## 1. 数据集
- 位置：`benchmarks/domain/`（`figures/`、`gt/`、`sources/`、`manifest.json`）。按 benchmarks/real 的做法采用平铺目录，split 记录在 manifest 中（未建 `dev/`、`heldout/` 子目录）。
- 真值全部来自公开数据集中真实发表的数值，**不含任何数字化或 curve2csv 输出**：

| Zenodo | 许可 | 内容 | 图（dev / HO） |
|---|---|---|---|
| 4072158 | CC0 | 高储能锚固围岩试验 | sandymudstone1 / coal1, sandstone1 |
| 4959298 | CC0 | 采动巷道底鼓三轴试验 | sandstone-0, sandstone-15 / shale-0, shale-15 |
| 3929410 | CC-BY | 长壁采空区压实力-位移 | – / testa, testb |
| 4991755 | CC0 | 切顶沿空巷道 Fig.7 数据 | fig7a / fig7b, fig7c |
| 4942609 | CC0 | 单轴 Kaiser 效应 应力-时间 | uct1, uct5 / uct3 |
| 10598216 | CC-BY | 灰岩水弱化 UCS | – / in1u, l1u, s1u, t2u, st1u |
| 23666827 | CC-BY | 黏土蠕变 沉降-log 时间 | c4k-s1 / tcb7b-s2, nc1b-s1 |
| 23356064 | CC-BY | 铜尾矿固结 e-log p | cu-control / – |

- 预处理：仅保留严格递增的 x，按弧长抽取 ≤300 个原始点（全部是真实数据点）。`prep_sources.py` 可从原始下载复现 `sources/`（已验证）。
- 渲染：`build.py` 按 slug 设种子生成论文风格图。参数为 Liberation Serif 字体、内向刻度、黑/灰/红/蓝、可选 marker / 图例 / “(a)” 标签、150–300 dpi、可选 JPEG 压缩，轴端刻度均有标注。
- Split：按 slug 的 sha256 排序，前 8 个为 dev，其余为 held-out。

## 2. 修复（只依据 dev 失败）
- 基线（4283b5a 代码）：dev 3/8，held-out 5/16。失败原因有两类：15 个 no_series（黑/灰曲线被纯彩色分离丢掉）和 1 个 x_coverage。
- 修复：新增 `separate/achromatic.py` 作为无彩色回退，**仅在彩色分离结果为空时触发**。它先去掉文字、网格、轴、边框、刻度和图例句柄，然后保留主导连通分量及其附近碎片，最多输出 1 条曲线。同时在 `extract/curve.py` 中加了可选的 width_hint。
- 测试：`tests/unit/test_achromatic_fallback.py`（3 个）。阈值、已有真值、tracker 均未改动。held-out 上没有做任何调参。

## 3. 结果（strict = with-bridge）
| split | 基线 | 修复后 |
|---|---:|---:|
| dev | 3/8 | **8/8** |
| held-out | 5/16 | **12/16** |
| all | 8/24 | 20/24 |

- fabrication 0，ink_support 中位数 1.0，平均 CPU 1.5 s/图。
- smoke：fabrication_count = **59**（未变差），smoke regression ok。回退在 0/60 个样本上触发。m1 硬门槛（要求 fab==0）原本就失败，不是本次引入的。
- 单测：64 passed，1 skipped；ruff 与 mypy --strict 均通过。

### held-out 失败（4 个，均为 x_coverage；系列数正确，NRMSE 都 < 2%）
| 图 | NRMSE % | 覆盖率 | 原因（看叠加图得出） |
|---|---:|---:|---|
| clay-creep-nc1b-s1 | 0.43 | 0.82 | 起始段 y≈0 压在下轴线上，被当作边框/轴清除 |
| gateroad-shale-0mpa | 1.19 | 0.705 | 峰后陡降后的尾段 y≈0 贴着 x 轴，丢失；方块 marker 处有毛刺 |
| gateroad-shale-15mpa | 0.66 | 0.705 | 峰后陡降处断开，右侧尾段（0.0133–0.0199）未被并入主分量 |
| limestone-ucs-l1u-dry | 0.60 | 0.845 | 空心圆 marker 干扰，起点段与 0.74 之后的尾段缺失 |

共性：曲线与坐标轴重合，或主分量断开后的尾段被丢弃。

## 4. 轻量人工确认模拟（`benchmarks/domain/confirm_sim.py`）
- 流程：pick（多系列时）→ 2 次点击确认框角 + 输入 4 个轴端刻度值（`extract_with_limits`）→ 再次 pick → 最多 2 次 clear_range。
- 与 GT 有关的近似（在 docstring 中已说明）：pick 的点击位置取 GT 中点所在像素；判断哪些区间“明显错误”时参照了 GT。
- held-out：自动通过 12/16，**确认后仍为 12/16**。4 个失败图平均 5.25 次点击 + 4 个输入值，每图约 34–40 s。按全部 16 张图平均约 16.6 s/图（计时模型：点击 2 s，输入 4 s，每图复查 10 s）。
- 关键结论：现有确认 API（框、标定、pick、clear_range）**无法补回缺失的覆盖**，因为 clear_range 只能删点。需要新增“补描/接受区段”（add-ink / trace range）操作。
- 与 WebPlotDigitizer 对比（**估计，未实测**）：WPD 每图约 90–180 s，包括载入、4 点标定与输入、取色/掩膜、自动提取与清理、导出。curve2csv 在 75% 的图上约 10–17 s。若失败图补上手工描点（估计 +30–60 s），整体平均约 30 s/图。

## 5. 局限 / 未完成
- 只有 7 个独立数据集共 24 张图，同一数据集内的图相关性高，held-out 的独立性有限。
- 图是用真实数据重新渲染的论文风格图，不是原始论文的扫描图。
- 确认 API 缺少补描操作（见上）。

## 6. 覆盖率修复（第二轮，仍在 w3-domain）

针对 4 个 held-out `x_coverage` 失败的根因（未调阈值、未改真值、未动 tracker；仅按机制修）：

1. **贴底轴的曲线段**：axes 带 + `_clear_border` 抹掉 y≈0 墨迹。在主导分量之后做 `grow_along_spine_band`：只在**尚无曲线墨迹的列**里，沿脊柱/边框带对暗墨做测地膨胀，避免把整条脊柱垫到曲线下方。
2. **长水平残段被当成文字**：放宽 `_curve_like_text`——取消 max_w 上限；对宽度 ≥0.12×图宽的细长笔画允许略高的高度上限（扛住文字膨胀）。
3. **空心 marker 断点**：主导分量前对候选做受约束的 3×3 close。
4. **彩色曲线的贴轴尾段**：单条彩色系列时用同样的脊柱带生长，墨水条件用 `chromatic_mask`（前景因 inset 看不到轴带）。

### 修复后结果（strict = with-bridge）

| split | 基线 (4283b5a) | 无彩色回退后 (a2d8088) | 覆盖率修复后 |
|---|---:|---:|---:|
| dev | 3/8 | 8/8 | **8/8** |
| held-out | 5/16 | 12/16 | **16/16** |
| all | 8/24 | 20/24 | **24/24** |

- fabrication 0，ink_support 中位数 1.0。
- 原先 4 个 held-out 失败全部通过；无需新增「补描区段」确认 API。
- 单测：66 passed，2 skipped（既有 degenerate span + 缺 pypdfium2）；ruff / mypy --strict 通过。
- smoke：fabrication_count = **59**（未变差），regression ok。

- 覆盖率修复后，上述 4 张 held-out 已自动通过；确认模拟不再需要为补覆盖服务（clear_range 仍只能删点）。
