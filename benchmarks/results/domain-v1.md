# Real-figure results (domain-single-curve-v1)

Commit `a2d8088fe23be4348ae0590de04ea60c01f86ba4`. Python 3.13.5.

Strict scoring drops every flagged point, including occlusion bridges. With-bridge scoring keeps points flagged `INTERPOLATED` and still drops every other flag. A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90.

`fabrication_count` is report-only here: unflagged, confidence ≥ 0.5 points outside the published axis ranges. OWID ground truth has no invisible-range masks, so this is narrower than the synthetic fabrication counter and does not change pass/fail. `ink_support` is the fraction of measured (non-empty, non-bridged) points with same-color ink within 2 px; it is also report-only.

| split | n | strict | strict accuracy | with-bridge | with-bridge accuracy |
|---|---:|---:|---:|---:|---:|
| dev | 8 | 8 | 100.00% | 8 | 100.00% |
| held-out | 16 | 16 | 100.00% | 16 | 100.00% |
| all | 24 | 24 | 100.00% | 24 | 100.00% |

Mean CPU time 1.243s/image. Bridged points: 0. Report-only fabrication points: 0.

Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:

- dev: n_fit=1, median |Δslope|/|slope|=0.007, median |Δintercept|/range=0.001, median ink_support=1.000, fabrication=0
- held-out: n_fit=0, median |Δslope|/|slope|=n/a, median |Δintercept|/range=n/a, median ink_support=1.000, fabrication=0
- all: n_fit=1, median |Δslope|/|slope|=0.007, median |Δintercept|/range=0.001, median ink_support=1.000, fabrication=0

## Per figure

| slug | split | strict | reason | bridge | bridge reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | bridge NRMSE % | bridge x-coverage | bridged | fab | ink support | license | url |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| anchor-coal1 | held-out | yes | ok | yes | ok | 1 | 1 | 0.208 | 0.995 | 0.208 | 0.995 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4072158 |
| anchor-sandstone1 | held-out | yes | ok | yes | ok | 1 | 1 | 0.394 | 0.995 | 0.394 | 0.995 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4072158 |
| anchor-sandymudstone1 | dev | yes | ok | yes | ok | 1 | 1 | 0.219 | 0.995 | 0.219 | 0.995 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4072158 |
| clay-creep-c4k-s1 | dev | yes | ok | yes | ok | 1 | 1 | 0.558 | 0.925 | 0.558 | 0.925 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.23666827 |
| clay-creep-nc1b-s1 | held-out | yes | ok | yes | ok | 1 | 1 | 0.421 | 1.000 | 0.421 | 1.000 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.23666827 |
| clay-creep-tcb7b-s2 | held-out | yes | ok | yes | ok | 1 | 1 | 0.835 | 0.965 | 0.835 | 0.965 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.23666827 |
| gateroad-sandstone-0mpa | dev | yes | ok | yes | ok | 1 | 1 | 0.775 | 0.945 | 0.775 | 0.945 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4959298 |
| gateroad-sandstone-15mpa | dev | yes | ok | yes | ok | 1 | 1 | 0.390 | 0.990 | 0.390 | 0.990 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4959298 |
| gateroad-shale-0mpa | held-out | yes | ok | yes | ok | 1 | 1 | 1.078 | 0.910 | 1.078 | 0.910 | 0 | 0 | 0.998 | CC0-1.0 | https://doi.org/10.5281/zenodo.4959298 |
| gateroad-shale-15mpa | held-out | yes | ok | yes | ok | 1 | 1 | 0.566 | 0.985 | 0.566 | 0.985 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4959298 |
| gob-compaction-testa | held-out | yes | ok | yes | ok | 1 | 1 | 1.275 | 0.925 | 1.275 | 0.925 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.3929410 |
| gob-compaction-testb | held-out | yes | ok | yes | ok | 1 | 1 | 0.388 | 0.995 | 0.388 | 0.995 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.3929410 |
| kaiser-uct1 | dev | yes | ok | yes | ok | 1 | 1 | 0.280 | 0.990 | 0.280 | 0.990 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4942609 |
| kaiser-uct3 | held-out | yes | ok | yes | ok | 1 | 1 | 0.748 | 0.945 | 0.748 | 0.945 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4942609 |
| kaiser-uct5 | dev | yes | ok | yes | ok | 1 | 1 | 0.414 | 0.995 | 0.414 | 0.995 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4942609 |
| limestone-ucs-in1u-dry | held-out | yes | ok | yes | ok | 1 | 1 | 0.511 | 0.995 | 0.511 | 0.995 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.10598216 |
| limestone-ucs-l1u-dry | held-out | yes | ok | yes | ok | 1 | 1 | 0.577 | 0.995 | 0.577 | 0.995 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.10598216 |
| limestone-ucs-s1u-sat | held-out | yes | ok | yes | ok | 1 | 1 | 0.819 | 0.955 | 0.819 | 0.955 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.10598216 |
| limestone-ucs-st1u-sat | held-out | yes | ok | yes | ok | 1 | 1 | 0.297 | 1.000 | 0.297 | 1.000 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.10598216 |
| limestone-ucs-t2u-sat | held-out | yes | ok | yes | ok | 1 | 1 | 0.340 | 1.000 | 0.340 | 1.000 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.10598216 |
| oedometer-cu-control | dev | yes | ok | yes | ok | 1 | 1 | 0.332 | 1.000 | 0.332 | 1.000 | 0 | 0 | 1.000 | CC-BY-4.0 | https://doi.org/10.5281/zenodo.23356064 |
| roofcut-pillar-fig7a | dev | yes | ok | yes | ok | 1 | 1 | 0.685 | 0.985 | 0.685 | 0.985 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4991755 |
| roofcut-pillar-fig7b | held-out | yes | ok | yes | ok | 1 | 1 | 0.791 | 0.985 | 0.791 | 0.985 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4991755 |
| roofcut-pillar-fig7c | held-out | yes | ok | yes | ok | 1 | 1 | 0.877 | 0.985 | 0.877 | 0.985 | 0 | 0 | 1.000 | CC0-1.0 | https://doi.org/10.5281/zenodo.4991755 |
