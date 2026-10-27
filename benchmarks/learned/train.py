"""Train the tiny segmenter on synthetic charts and export ONNX.

One short run. Threshold and tau are chosen on the synthetic validation
charts. This module does not read ``benchmarks/real``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn

from benchmarks.learned.render import CANVAS, RenderedChart, render_chart

SEED = 20261025
CROP = 256


class TinySegmenter(nn.Module):
    """Full-resolution dilated stack. Output is ink logit plus an 8-d embedding.

    The embedding is ``normalize(color(rgb) + spatial(features))``. Spatial
    weights start at zero, so training begins as a color embedding.
    """

    def __init__(self) -> None:
        super().__init__()
        channels = (3, 16, 24, 32, 32)
        dilations = (1, 2, 4, 8)
        blocks: list[nn.Module] = []
        for index, dilation in enumerate(dilations):
            blocks.append(
                nn.Conv2d(
                    channels[index],
                    channels[index + 1],
                    kernel_size=3,
                    padding=dilation,
                    dilation=dilation,
                )
            )
            blocks.append(nn.ReLU())
        self.trunk = nn.Sequential(*blocks)
        self.ink = nn.Conv2d(32, 1, kernel_size=1)
        self.spatial = nn.Conv2d(32, 8, kernel_size=1)
        self.color = nn.Conv2d(3, 8, kernel_size=1)
        nn.init.zeros_(self.spatial.weight)
        nn.init.zeros_(self.spatial.bias)
        nn.init.zeros_(self.color.weight)
        nn.init.zeros_(self.color.bias)
        with torch.no_grad():
            for channel in range(3):
                self.color.weight[channel, channel, 0, 0] = 1.0
            self.color.bias[3] = 0.5
            self.ink.bias.fill_(-2.0)

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        features = self.trunk(image)
        ink = self.ink(features)
        embed = self.color(image) + self.spatial(features)
        embed = embed / (embed.norm(dim=1, keepdim=True) + 1e-6)
        return torch.cat([ink, embed], dim=1)


def _crop(chart: RenderedChart, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    height, width = chart.label.shape
    if float(rng.random()) < 0.85 and int(chart.label.max()) > 0:
        ys, xs = np.nonzero(chart.label)
        pick = int(rng.integers(0, ys.size))
        center_y = int(ys[pick])
        center_x = int(xs[pick])
    else:
        center_y = int(rng.integers(0, height))
        center_x = int(rng.integers(0, width))
    y0 = int(np.clip(center_y - CROP // 2, 0, height - CROP))
    x0 = int(np.clip(center_x - CROP // 2, 0, width - CROP))
    return (
        chart.rgb[y0 : y0 + CROP, x0 : x0 + CROP],
        chart.label[y0 : y0 + CROP, x0 : x0 + CROP],
    )


def _batch(
    charts: list[RenderedChart], rng: np.random.Generator, batch: int
) -> tuple[torch.Tensor, torch.Tensor]:
    images: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    for _ in range(batch):
        chart = charts[int(rng.integers(0, len(charts)))]
        rgb, label = _crop(chart, rng)
        images.append(np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1)))
        labels.append(label.astype(np.int64))
    image = torch.from_numpy(np.stack(images))
    target = torch.from_numpy(np.stack(labels))
    return image, target


def _instance_loss(embed: torch.Tensor, label: torch.Tensor) -> torch.Tensor:
    """Pull a series together and push series means apart."""

    terms: list[torch.Tensor] = []
    for batch_index in range(label.shape[0]):
        ids = [int(v) for v in torch.unique(label[batch_index]).tolist() if int(v) > 0]
        means: list[torch.Tensor] = []
        pulls: list[torch.Tensor] = []
        for series_id in ids:
            selected = label[batch_index] == series_id
            if int(selected.sum()) < 8:
                continue
            vecs = embed[batch_index, :, selected].transpose(0, 1)
            mean = vecs.mean(dim=0)
            mean = mean / (mean.norm() + 1e-6)
            variance = ((vecs - mean) ** 2).sum(dim=1).mean()
            pulls.append(torch.relu(variance - 0.35))
            means.append(mean)
        if not pulls:
            continue
        pull = torch.stack(pulls).mean()
        push = embed.new_zeros(())
        if len(means) >= 2:
            pairs = []
            for left in range(len(means)):
                for right in range(left + 1, len(means)):
                    distance = (means[left] - means[right]).norm()
                    pairs.append(torch.relu(1.2 - distance))
            push = torch.stack(pairs).mean()
        terms.append(pull + push)
    if not terms:
        return embed.sum() * 0.0
    return torch.stack(terms).mean()


def _loss(output: torch.Tensor, label: torch.Tensor) -> tuple[torch.Tensor, float, float, float]:
    logit = output[:, 0]
    target = (label > 0).to(logit.dtype)
    pos = logit.new_tensor([12.0])
    bce = nn.functional.binary_cross_entropy_with_logits(logit, target, pos_weight=pos)
    prob = torch.sigmoid(logit)
    inter = (prob * target).sum()
    dice = 1.0 - (2.0 * inter + 1.0) / (prob.sum() + target.sum() + 1.0)
    inst = _instance_loss(output[:, 1:], label)
    total = bce + dice + 3.0 * inst
    return total, float(bce.detach()), float(dice.detach()), float(inst.detach())


@torch.no_grad()
def _val_dice(net: TinySegmenter, charts: list[RenderedChart], rng: np.random.Generator) -> float:
    net.eval()
    scores: list[float] = []
    for chart in charts:
        for _ in range(2):
            rgb, label = _crop(chart, rng)
            image = torch.from_numpy(np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1)))
            output = net(image[None])
            prob = torch.sigmoid(output[:, 0])
            target = torch.from_numpy((label > 0).astype(np.float32))[None]
            inter = (prob * target).sum()
            dice = (2.0 * inter + 1.0) / (prob.sum() + target.sum() + 1.0)
            scores.append(float(dice))
    net.train()
    return float(np.mean(scores)) if scores else 0.0


def _sanity(chart: RenderedChart) -> None:
    counts = [int((chart.label == index).sum()) for index in range(1, chart.n_series + 1)]
    print(f"sanity counts={counts} style={chart.style}", flush=True)
    if not counts or max(counts) < 30:
        raise SystemExit("label pixels do not sit on the series color")


def _matched_dice(masks: list[np.ndarray], label: np.ndarray) -> float:
    from scipy.optimize import linear_sum_assignment

    ids = [int(v) for v in np.unique(label) if int(v) > 0]
    if not ids and not masks:
        return 1.0
    if not ids or not masks:
        return 0.0
    gt = [label == series_id for series_id in ids]
    cost = np.zeros((len(masks), len(gt)), dtype=np.float64)
    for i, pred in enumerate(masks):
        for j, truth in enumerate(gt):
            inter = np.logical_and(pred, truth).sum()
            total = pred.sum() + truth.sum()
            dice = 1.0 if total == 0 else (2.0 * inter) / total
            cost[i, j] = 1.0 - dice
    rows, cols = linear_sum_assignment(cost)
    matched = float(sum(1.0 - cost[i, j] for i, j in zip(rows, cols, strict=True)))
    return matched / max(len(ids), len(masks))


def _sweep(net: TinySegmenter, charts: list[RenderedChart]) -> tuple[float, float, float]:
    from curve2csv.separate.learned import masks_from_output

    net.eval()
    outputs: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    with torch.no_grad():
        for chart in charts:
            image = torch.from_numpy(np.transpose(chart.rgb.astype(np.float32) / 255.0, (2, 0, 1)))
            output = net(image[None])[0].numpy()
            outputs.append((output, chart.rgb, chart.label))
    best = (0.5, 0.7, -1.0)
    for threshold in (0.35, 0.5):
        for tau in (0.5, 0.7, 0.9):
            scores = []
            for output, rgb, label in outputs:
                masks = masks_from_output(
                    output, rgb, None, threshold=threshold, tau=tau, max_series=6, min_pixels=40
                )
                scores.append(_matched_dice(masks, label))
            mean = float(np.mean(scores)) if scores else 0.0
            print(f"sweep threshold={threshold:.2f} tau={tau:.1f} dice={mean:.4f}", flush=True)
            if mean > best[2]:
                best = (threshold, tau, mean)
    return best


def train(out_dir: Path, steps: int, n_train: int, n_val: int) -> None:
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    render_rng = np.random.default_rng(SEED)
    train_rng = np.random.default_rng(SEED + 1)
    val_rng = np.random.default_rng(SEED + 2)
    print(f"rendering {n_train} train + {n_val} val charts at {CANVAS}", flush=True)
    probe = render_chart(render_rng)
    _sanity(probe)
    train_charts = [probe]
    for index in range(1, n_train):
        train_charts.append(render_chart(render_rng))
        if (index + 1) % 10 == 0:
            print(f"rendered train {index + 1}/{n_train}", flush=True)
    val_charts = [render_chart(render_rng) for _ in range(n_val)]
    print(f"rendered val {n_val}", flush=True)
    net = TinySegmenter()
    params = sum(int(p.numel()) for p in net.parameters())
    print(f"params {params}", flush=True)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    best_dice = -1.0
    best_state: dict[str, torch.Tensor] | None = None
    net.train()
    for step in range(steps):
        image, target = _batch(train_charts, train_rng, 8)
        opt.zero_grad(set_to_none=True)
        total, bce, dice, inst = _loss(net(image), target)
        if not torch.isfinite(total):
            print(f"step {step:04d} nonfinite loss", flush=True)
            continue
        total.backward()
        nn.utils.clip_grad_norm_(net.parameters(), 5.0)
        opt.step()
        if step % 20 == 0 or step + 1 == steps:
            print(
                f"step {step:04d} loss {float(total.detach()):.4f} "
                f"bce {bce:.4f} dice {dice:.4f} inst {inst:.4f}",
                flush=True,
            )
        if (step + 1) % 40 == 0 or step + 1 == steps:
            score = _val_dice(net, val_charts, val_rng)
            print(f"step {step:04d} val_dice {score:.4f}", flush=True)
            if score > best_dice:
                best_dice = score
                best_state = copy.deepcopy(net.state_dict())
    if best_state is not None:
        net.load_state_dict(best_state)
    print(f"best val_dice {best_dice:.4f}", flush=True)
    threshold, tau, sweep_dice = _sweep(net, val_charts)
    print(
        f"RECOMMEND learned_threshold={threshold:.2f} learned_tau={tau:.1f} "
        f"sweep_dice={sweep_dice:.4f}",
        flush=True,
    )
    net.eval()
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = out_dir / "segmenter.onnx"
    dummy = torch.zeros(1, 3, 64, 64)
    torch.onnx.export(
        net,
        dummy,
        str(onnx_path),
        input_names=["image"],
        output_names=["output"],
        dynamic_axes={
            "image": {0: "batch", 2: "height", 3: "width"},
            "output": {0: "batch", 2: "height", 3: "width"},
        },
        opset_version=17,
        dynamo=False,
    )
    digest = hashlib.sha256(onnx_path.read_bytes()).hexdigest()
    (out_dir / "segmenter.sha256").write_text(digest + "\n", encoding="utf-8")
    print(f"wrote {onnx_path} bytes={onnx_path.stat().st_size} sha256={digest}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="benchmarks.learned.train")
    parser.add_argument("--out", type=Path, default=Path("/tmp/learned-m25"))
    # 180 steps stays on the flat part of the ink loss. 400 crosses it.
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--train-charts", type=int, default=80)
    parser.add_argument("--val-charts", type=int, default=8)
    args = parser.parse_args()
    train(args.out, args.steps, args.train_charts, args.val_charts)


if __name__ == "__main__":
    main()
