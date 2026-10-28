# Held-out 失败诊断（PR #9）

诊断只读。提取器、桥接长度、切分和通过规则都没有改。分数来自 `benchmarks/results/real-v1.json`，对应提交 `e7dc53d`（Python 3.12.3）。held-out 39/61 通过，失败 22 张；全体 71/110。严格评分和 with-bridge 评分的通过数相同。这 22 张里，with-bridge 只改动了 `annual-fish-catch-taxa` 的 NRMSE（0.397 → 0.418），覆盖率不变，没有一张因此通过。

通过规则：预测系列数等于真值系列数，且每条系列 NRMSE ≤ 2% 轴量程、x-coverage ≥ 0.90。`fabrication_count` 硬门禁仍是 0。桥接点带 `interpolated=1`，严格评分丢掉它们。

这 22 张在 `e7dc53d` 上重新提取过。QA 叠图和「原图 + CSV/预测」对照图在产物包 `heldout-fail-qa.zip`（每张 `<slug>.overlay.png` 与 `<slug>.compare.png`）。原图路径是 `benchmarks/real/figures/<slug>.png`。

墨迹对照的做法：在预测点的列上找与该系列颜色 CIEDE2000 < 22 的像素，取中位行，再把官方 CSV 用本次标定映回像素。中位差接近 0 表示描线贴着墨迹。

## 给决定用的摘要

| 类别 | 张数 | 代表 | 判断 | 若只修这一类，held-out 估计能多通过 |
|---|---:|---|---|---:|
| 笔画在，却被收成散点 | 2 | `cumulative-space-visits`、`land-natural-share` | 可修。其它系列已经通过，留下的点 NRMSE 远低于 2 | +2 |
| 描线贴墨，CSV 在局部离开墨迹 | 5 | `global-smallpox-cases`、`diphtheria-cases-in-the-united-states`、`uk-gdp-growth-19572016` | 对基准，不靠跟踪去贴 CSV | 0 |
| 贴墨、差一点点到 0.90 | 1 | `growth-of-global-trade` | 描线已经在墨上，尾部大约 7–13 px 超出 2% | 0 |
| 色线比 CSV 短，或 y 刻度不含真值下界 | 3 | `wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000`、`same-sex-marriage-country-count`、`mention-of-the-word-capitalism-in-new-york-times-articles` | 缺的那一段没有该系列的色墨。补出来就是造点 | 0 |
| 坐标读不上或图框错了 | 4 | `co2-long-term-concentration`、`nitrous-oxide-long`、`cases-of-paralytic-polio-from-wild-polioviruses`、`wildlife-exports` | 先决条件是轴或图框。修完之后的曲线分数没有测 | 不计入 |
| 一条线缺段，其余系列已通过 | 1 | `maize-production`（欧盟） | 跟上的部分 NRMSE 0.14。缺的是不是连续色线，没有逐列核完 | 最多 +1，未测 |
| 多条线互相穿插或贴得很近 | 3 | `annual-fish-catch-taxa`、`breast-cancer-death-rate-in-women`、`difference-in-female-and-male-life-expectancy-at-age-45` | 每张有 3–4 条同时低于 0.90。加长短桥盖不住 | 0 |
| 系列数不对，补系列仍过不了 | 2 | `marriage-rate-per-1000-inhabitants`、`microplastics-in-ocean` | 结婚率的波兰 NRMSE 已是 3.87。微塑料 2020 年前是同一条红线 | 0 |
| 轴刻度缺 0，同时缺系列 | 1 | `cashew-nut-yields` | y 刻度从 2 起，真值从 0 起；中国没有预测系列 | 0 |

上面的「+2」和「最多 +1」是判断，不是改完再跑出来的分数。最清楚的下一步是散点/折线分类：俄罗斯和德国的色墨分别覆盖 475 和 452 列，输出却只有 31 和 36 个散点。只做这一类，held-out 大约从 39/61 到 41/61，离 90%（55/61）还远。

### 实测（`c567941`）

这条已经做了，假设的 +2 没有出现。held-out 仍是 39/61，全体仍是 71/110，严格和 with-bridge 相同，原先通过的图没有退回。两张都改成了折线，NRMSE 很低，覆盖率还不到 0.90：

- `cumulative-space-visits` 俄罗斯：31 个散点、覆盖率 0.075 → 532 个未标记点、覆盖率 0.855、NRMSE 0.139。剩下的空洞主要是 1961–1965，画面上没有这条颜色的墨。
- `land-natural-share` 德国：36 个散点、覆盖率 0.115、NRMSE 0.21 → 463 个点、覆盖率 0.725、NRMSE 0.089。其余空洞是蒙版里没有的列。

`wildlife-exports` 的错图框里有一块同样的细碎笔画，NRMSE 从 30.8 变成 37.5，原因仍是 series_count。smoke 与 `e7dc53d` 相同：`fabrication_count` 59，`bridged_count` 92，`curve_nrmse_range_median` 0.859。

### 空洞逐列（`c567941` 之后，提取器未再改）

评分用的 200 个采样点里，对不上的点按「预期 y 上下 6px 内有没有本系列的墨」分类。短桥规则不变：缺口超过线宽加 2px 的不补。

`cumulative-space-visits` 俄罗斯，覆盖率 0.855，对不上 29/200。其它三条已通过。

| 年份 | 采样点 | 分类 |
|---|---:|---|
| 1961–1964.3 | 13 | 无本色墨。预期位置上是另一条系列的棕色 `[153,109,57]`（与俄罗斯 ΔE 19.6），整列也没有更近的橙色 |
| 1964.6–1965.5、2004.7、2018 | 5 | 像素属于另一条系列（`s3`），ΔE 13.8，不是俄罗斯蒙版 |
| 1978.2–1979.4 | 5 | 无本色墨。14 列都是同一条棕色，宽于线宽加 2px，不能短桥 |
| 1982.4–1982.7 | 2 | 无本色墨，最近像素 ΔE 24 |
| 2020.1 | 1 | 蒙版里有墨，清理时被丢掉 |
| 2020.4–2021 | 3 | 纯橙色 `[177,53,7]` 在图框右缘之外（框右端 x=712，墨在 712–719），不在任何系列蒙版里 |

把蒙版里没画上的 2 个点和框外的 3 个纯色点都算上，覆盖率到 0.880。再把另外 5 个属于别的系列的点算进来才到 0.905。那 5 个不能算本系列的墨。其余 19 个点整列都没有俄罗斯的颜色。这张图在现有规则下过不了 0.90。

`land-natural-share` 德国，覆盖率 0.725，对不上 55/200。其它三条已通过。德国的颜色是蒙版的 Lab `[50.1, 13.0, 35.2]`，不是旁边那条更亮的橙色。

| 分类 | 采样点 | 若收回，覆盖率 |
|---|---:|---:|
| 已对齐 | 145 | 0.725 |
| 原始蒙版里有、离预期 y ≤ 6px，但被图例手柄规则删掉或短段被丢掉 | 21 | 0.830 |
| 不在蒙版里、ΔE 12–18 的邻色边缘 | 8 | 0.870 |
| 预期 y 附近没有本色墨（同色像素在 70–88px 之外，是另一条线） | 26 | 到不了 0.90 |

最大的两段是 1951–1968（16 点）和 1983–1989（6 点），预期 y 上最近的像素 ΔE 19–36。短桥盖不住。德国在现有规则下也过不了 0.90。提取器因此没有再改。

### 单系列刻度（`e5dcdf7`）

held-out 里真值只有 1 条系列的图是 46 张，原先通过 35 张。`co2-long-term-concentration` 因 `803.719BCE` 这种标签没被解析而 `no_calibration`；外缘对齐之后 NRMSE 0.985、覆盖率 0.920，通过。单系列 held-out 变为 36/46。`nitrous-oxide-long` 现在能标定，NRMSE 5.19、覆盖率 0.375，仍失败。其余单系列失败仍是描线与 CSV 不一致，或色线短于 CSV。

专门计数：

- 失败原因：`x_coverage` 8，`nrmse_and_coverage` 7，`series_count` 4，`no_calibration` 3。
- 整图最差覆盖率落在 0.70–0.89 的有 5 张：`growth-of-global-trade` 0.870，`diphtheria-cases-in-the-united-states` 0.835，`rubella-cases-in-the-united-states` 0.800，`marriage-rate-per-1000-inhabitants` 0.710，`wage-of-craftsmen-...` 0.700。其中只有全球贸易这一张 NRMSE 已经 ≤ 2 且描线贴着墨。白喉和风疹是 CSV 尖峰，结婚率的门是系列数，工资的尾巴没有色墨。
- 描线贴墨、CSV 仍明显离开墨迹：5 张（天花、白喉、风疹、英国 GDP、长期冲突死亡率）。全球贸易是同一现象的轻量版，另计。
- `series_count`：4 张。四张都不是「补上一条系列就会通过」。

## 22 张失败

NRMSE 和 coverage 是该图已配对系列里最差的一条。严格和 with-bridge 的通过标记都是失败。

| 图 | 原因 | 真值系列 | 预测系列 | 严格 NRMSE | 严格 coverage | with-bridge NRMSE | with-bridge coverage | 桥接点 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `annual-fish-catch-taxa` | x_coverage | 5 | 5 | 0.397 | 0.635 | 0.418 | 0.635 | 17 |
| `breast-cancer-death-rate-in-women` | x_coverage | 6 | 6 | 0.161 | 0.620 | 0.161 | 0.620 | 3 |
| `cases-of-paralytic-polio-from-wild-polioviruses` | no_calibration | 5 | 0 | — | — | — | — | 0 |
| `cashew-nut-yields` | series_count | 4 | 3 | 7.618 | 0.005 | 7.618 | 0.005 | 0 |
| `co2-long-term-concentration` | no_calibration | 1 | 0 | — | — | — | — | 0 |
| `cumulative-space-visits` | x_coverage | 4 | 4 | 0.597 | 0.075 | 0.597 | 0.075 | 0 |
| `difference-in-female-and-male-life-expectancy-at-age-45` | x_coverage | 4 | 4 | 0.943 | 0.390 | 0.943 | 0.390 | 0 |
| `diphtheria-cases-in-the-united-states` | nrmse_and_coverage | 1 | 1 | 3.646 | 0.835 | 3.646 | 0.835 | 0 |
| `global-death-rate-in-violent-political-conflicts-over-the-long-run` | nrmse_and_coverage | 1 | 1 | 12.627 | 0.230 | 12.627 | 0.230 | 0 |
| `global-smallpox-cases` | nrmse_and_coverage | 1 | 1 | 6.145 | 0.655 | 6.145 | 0.655 | 0 |
| `growth-of-global-trade` | x_coverage | 1 | 1 | 1.527 | 0.870 | 1.527 | 0.870 | 0 |
| `land-natural-share` | x_coverage | 4 | 4 | 0.208 | 0.115 | 0.208 | 0.115 | 5 |
| `maize-production` | x_coverage | 5 | 5 | 1.430 | 0.585 | 1.430 | 0.585 | 3 |
| `marriage-rate-per-1000-inhabitants` | series_count | 5 | 4 | 3.867 | 0.710 | 3.867 | 0.710 | 4 |
| `mention-of-the-word-capitalism-in-new-york-times-articles` | nrmse_and_coverage | 1 | 1 | 5.982 | 0.255 | 5.982 | 0.255 | 0 |
| `microplastics-in-ocean` | series_count | 3 | 2 | 0.285 | 0.175 | 0.285 | 0.175 | 0 |
| `nitrous-oxide-long` | no_calibration | 1 | 0 | — | — | — | — | 0 |
| `rubella-cases-in-the-united-states` | nrmse_and_coverage | 1 | 1 | 3.047 | 0.800 | 3.047 | 0.800 | 0 |
| `same-sex-marriage-country-count` | x_coverage | 1 | 1 | 1.141 | 0.530 | 1.141 | 0.530 | 0 |
| `uk-gdp-growth-19572016` | nrmse_and_coverage | 1 | 1 | 7.211 | 0.470 | 7.211 | 0.470 | 0 |
| `wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000` | nrmse_and_coverage | 1 | 1 | 2.629 | 0.700 | 2.629 | 0.700 | 0 |
| `wildlife-exports` | series_count | 6 | 5 | 30.803 | 0.000 | 30.803 | 0.000 | 5 |

## 逐张

### 笔画在，输出却是散点

`cumulative-space-visits`。世界、美国、日本是折线并且已经通过。俄罗斯被收成 31 个散点，覆盖率 0.075，这 31 个点的 NRMSE 是 0.133。同色墨迹占了图框里 475 列（图框宽 666）。失败模式是连接标记的笔画被丢掉，只剩标记。

`land-natural-share`。世界、法国、英国的覆盖率是 0.995–1.000，NRMSE ≤ 0.10。德国被收成 36 个散点，覆盖率 0.115，这 36 个点的 NRMSE 是 0.21。同色墨迹 452 列。桥接 5 个点，没有补上这条线。

### 描线贴着墨，CSV 在局部对不上

这五张的预测点与同色墨的中位距离都在 1 px 左右。把 CSV 用本次标定映回像素后，中位差也接近 0，但高分位到了几十像素。误差集中在少数尖峰或来回抖动的年份，不是整条线平移。

`global-smallpox-cases`。线性轴，刻度残差 x 0.010、y 0.002。墨迹对预测的中位差 −0.5 px。CSV 对墨迹的中位差 −0.6 px，90 分位 43 px。大约 1920s 后段有一段约 +28 px 的偏离，其余年份贴着线。覆盖率 0.655 来自这些尖峰超过 2%，同时有少量列对不齐。

`diphtheria-cases-in-the-united-states`。同样贴墨（中位 −0.5 px）。CSV 对墨迹中位 −0.1 px，90 分位 25 px。一段约 9% 跨度的年份中位偏离 −28 px，覆盖率因此停在 0.835。这是 0.70–0.89 带里的一张，原因是 CSV 尖峰，不是缺一条缝。

`rubella-cases-in-the-united-states`。年份轴被收成 log10（线性拟合残差 0.012，log 拟合 0.014，两者都低于 0.02 门限）。把同一批像素改用线性年份再评分，NRMSE 3.16、覆盖率仍是 0.80，比现在的 3.05 / 0.80 更差。所以 log 选择不是这张的杠杆。墨迹对 CSV 的中位差 −0.1 px，90 分位 32 px，有一段约 −29 px。覆盖率 0.800 同样是尖峰，不是缺段。

`uk-gdp-growth-19572016`。轴端点只差 2–4 px，刻度残差合格。描线 626 个点铺满图框，与墨的中位差 −0.5 px。CSV 对墨的中位差 −1.6 px，90 分位 60 px。大约一半采样的 y 误差超过 2%，来回有十几像素的偏差，不是一条平移。覆盖率 0.470。

`global-death-rate-in-violent-political-conflicts-over-the-long-run`。真值和预测都是 y 对数。三条 y 刻度 0.1、10、100 的对数拟合残差 0.002。描线贴墨（中位 0 px）。CSV 映回后与墨的中位差 9.7 px，90 分位 48 px。曲线本身很碎，官方序列和画面上的折线不是同一条轨迹。覆盖率 0.230，NRMSE 12.6。

`growth-of-global-trade` 放在这里的轻量端。NRMSE 1.527 已经通过，覆盖率 0.870，未对齐只有 1%。描线 765 点，与墨的中位差 −0.5 px；CSV 对墨的中位差 0.2 px，90 分位 6.9 px。2% 量程大约是 7 px。尾部上升段有大约 12 px 的一块超出。y 刻度读到 0、500、1000、1500、2000，真值上界是 2500，外推之后尾部仍和墨差这一截。再跟踪不会在不离开墨迹的前提下跨过 0.90。

### 色线比 CSV 短，或刻度下界低于画面

`wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000`。同色墨停在图框大约 89% 处，预测 x 最大约 1909，真值到 2000。y 方向读到的刻度是 1.4、1.6、1.8、2.2，真值范围从 1.0 起，图框底被映到 1.39。重叠年份的中位绝对误差约 2.4 px，尾巴既没有色墨，CSV 又往下走。NRMSE 2.629，覆盖率 0.700。

`same-sex-marriage-country-count`。图框左 40% 没有该系列颜色的墨，色线从大约 2009 年开始（预测 x 从 2009.8 起），CSV 从 2000、接近 0 起。y 刻度读到 10–40，没有 0，真值范围是 0–40。NRMSE 1.141 已通过，覆盖率 0.530 几乎全是这段没有色墨的开头。

`mention-of-the-word-capitalism-in-new-york-times-articles`。预测 x 从 1917 起，真值从 1851 起。图框最左四分之一只有 17 列同色墨，预测点是 0。y 刻度从 0.4 到 1.6，没有 0，真值下界是 0.09。把 CSV 按图框铺到真值范围上，与墨的中位差约 −48 px。开头缺的是色线，不是一条被误删的密笔画。

### 坐标或图框

`co2-long-term-concentration`。图区检测放弃（`no_axis_found`），标签框也没有。横轴是「803,719 BCE」这种带逗号和 BCE 的文字，当前解析器不把它们当刻度。画面是一条普通折线，右端有一根贴着 2025 的竖线。没有曲线分数。

`nitrous-oxide-long`。同一类 BCE 标签。另外图区检测锁在画面右侧一块斜的框 `(456, 302, 754, 557)` 上，`read_axes` 和 `read_frame` 都是空。没有曲线分数。

`cases-of-paralytic-polio-from-wild-polioviruses`。图框在，放弃原因是 `residual_too_high`。y 刻度 0 到 1600 的线性残差最大 0.001。x 刻度 2001、2005、2010、2015、2020、2023 对一条直线的最大相对残差是 0.054，出在 2023 和 2020 的间距上。五条线互相交叉。轴能标定之后会不会通过，没有测。

`wildlife-exports`。主图在左侧，六条线都看得见。用到的图框是 `(332, 80, 646, 530)`，左边几十年在框外。落进这个框的 x 标签 1985、1990 被当成了 y 刻度，y 被映成 1825 到 −2665，真值是 0 到 800 万。报告的系列数 6→5 和 NRMSE 30.8 都是这个错框的结果。框对了以后的分数没有测。

`cashew-nut-yields`。y 刻度读到 2、3、4、5、7，真值范围 0–7，图框底被映到 1.95（底端点相差 123 px）。预测 3 条，缺中国。马里是 5 个散点，覆盖率 0.005。秘鲁、墨西哥的 NRMSE 是 3.4 和 7.0。系列数和轴是绑在一起的，只补中国不会通过。

### 缺段，但已经跟上的部分是准的

`maize-production`。美国、中国、印度、俄罗斯覆盖率 ≥ 0.975。欧盟覆盖率 0.585，未对齐 0.41，集中在跨度的 0–0.19 和 0.30–0.53，NRMSE 只有 0.136。它有 340 个点，其它满幅系列大约 588 个。桥接 3 个点。若缺的两段仍是这条线的色墨，这张有机会通过；这一点没有逐列核完。

`annual-fish-catch-taxa`。五条都在。金枪鱼覆盖率 0.95 已通过。鲭 0.88、虾 0.88、其他海鱼 0.82、饵料鱼 0.64。饵料鱼两段空洞大约在跨度的 0.21–0.34 和 0.45–0.61，未对齐 0.36，跟上的部分 NRMSE 0.23。17 个桥接点没有把任何一条抬过 0.90。空洞比「线宽 + 2 px」长得多，是缠在一起之后整段跟丢。

`breast-cancer-death-rate-in-women`。六条都在，跟上的部分 NRMSE ≤ 0.16。美国 0.90 刚好过。意大利 0.88，加拿大 0.67（后 33% 没有点），法国 0.62，南非 0.68（后段缺）。缺的是线尾，靠近右侧图例。3 个桥接点不够。

`difference-in-female-and-male-life-expectancy-at-age-45`。英国覆盖率 0.915 已通过。法国 0.39，两段早期空洞各约 30% 跨度。美国 0.83，瑞典 0.79。跟上的点大约差 1–2 px。这是几条长历史曲线贴在一起，不是短交叉。

### 系列数不是唯一的门

`marriage-rate-per-1000-inhabitants`。真值 5 条，预测 4 条，缺英国。美国已通过。墨西哥覆盖率 0.885。韩国 0.75，有两段未对齐。波兰 NRMSE 3.867，其中一段约 −49 px，然后线尾未对齐。把英国找回来，波兰仍然过不了 2%。

`microplastics-in-ocean`。三条情景在 2020 年之前共用一条红线，之后分成红、蓝、灰。预测只有红（增长情景，覆盖率 0.995）和蓝（持平情景，99 个点，82% 的跨度没有自己的墨，因为前半段是红的）。灰色的「2020 年停止」没有系列。把红线复制给蓝和灰才盖得住各自的 x 范围；那是同一块墨记到多条系列上，按不造点的规则不算可修。

## 和上一版结论的差别

`cumulative-space-visits` 的俄罗斯不是「标记之间的空白不能填」。同色墨迹有 475 列，分类器把它收成了散点。空白是分类结果，画面上的连接线还在。
