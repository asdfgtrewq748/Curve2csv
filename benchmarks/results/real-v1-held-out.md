# Real-figure results (owid-grapher-v1)

Commit `59b617155a93196e1a7de929fcfeb0b3066803df`. Python 3.13.5.

Strict scoring drops every flagged point, including occlusion bridges. With-bridge scoring keeps points flagged `INTERPOLATED` and still drops every other flag. A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90.

| split | n | strict | strict accuracy | with-bridge | with-bridge accuracy |
|---|---:|---:|---:|---:|---:|
| dev | 0 | 0 | n/a | 0 | n/a |
| held-out | 61 | 47 | 77.05% | 47 | 77.05% |
| all | 61 | 47 | 77.05% | 47 | 77.05% |

Mean CPU time 1.411s/image. Bridged points: 51.

Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:

- dev: n_fit=0, median |Δslope|/|slope|=n/a, median |Δintercept|/range=n/a
- held-out: n_fit=2, median |Δslope|/|slope|=0.009, median |Δintercept|/range=0.080
- all: n_fit=2, median |Δslope|/|slope|=0.009, median |Δintercept|/range=0.080

## Per figure

| slug | split | strict | reason | bridge | bridge reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | bridge NRMSE % | bridge x-coverage | bridged | license | url |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| annual-fish-catch-taxa | held-out | no | x_coverage | no | x_coverage | 5 | 5 | 0.396 | 0.635 | 0.418 | 0.635 | 17 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-fish-catch-taxa |
| annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar | held-out | yes | ok | yes | ok | 1 | 1 | 0.165 | 1.000 | 0.165 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar |
| annual-patents-invention-united-states-1790 | held-out | yes | ok | yes | ok | 1 | 1 | 0.562 | 0.960 | 0.562 | 0.960 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-patents-invention-united-states-1790 |
| arable-land-pin | held-out | yes | ok | yes | ok | 1 | 1 | 0.123 | 1.000 | 0.123 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/arable-land-pin |
| biomass-fish-stocks-taxa | held-out | yes | ok | yes | ok | 1 | 1 | 0.108 | 1.000 | 0.108 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/biomass-fish-stocks-taxa |
| breast-cancer-death-rate-in-women | held-out | no | x_coverage | no | x_coverage | 6 | 6 | 0.159 | 0.620 | 0.159 | 0.620 | 3 | CC BY 4.0 | https://ourworldindata.org/grapher/breast-cancer-death-rate-in-women |
| cases-of-paralytic-polio-from-wild-polioviruses | held-out | no | no_calibration | no | no_calibration | 5 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cases-of-paralytic-polio-from-wild-polioviruses |
| cashew-nut-yields | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.455 | 0.510 | 0.455 | 0.510 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cashew-nut-yields |
| cholera-case-fatality-rate | held-out | yes | ok | yes | ok | 1 | 1 | 0.661 | 0.950 | 0.661 | 0.950 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cholera-case-fatality-rate |
| co2-long-term-concentration | held-out | yes | ok | yes | ok | 1 | 1 | 0.985 | 0.920 | 0.985 | 0.920 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/co2-long-term-concentration |
| coal-output-per-worker-in-the-united-kingdom | held-out | yes | ok | yes | ok | 1 | 1 | 0.369 | 0.965 | 0.369 | 0.965 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/coal-output-per-worker-in-the-united-kingdom |
| cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 | held-out | yes | ok | yes | ok | 1 | 1 | 0.192 | 1.000 | 0.192 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 |
| countries-with-a-signed-bilateral-investment-treaty | held-out | yes | ok | yes | ok | 2 | 2 | 0.255 | 1.000 | 0.255 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-a-signed-bilateral-investment-treaty |
| countries-with-an-inforce-bilateral-investment-treaty | held-out | yes | ok | yes | ok | 2 | 2 | 0.245 | 0.960 | 0.245 | 0.960 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-an-inforce-bilateral-investment-treaty |
| cumulative-space-visits | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.597 | 0.855 | 0.597 | 0.855 | 5 | CC BY 4.0 | https://ourworldindata.org/grapher/cumulative-space-visits |
| deaths-and-disappearances-during-migration | held-out | yes | ok | yes | ok | 1 | 1 | 0.220 | 1.000 | 0.220 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-and-disappearances-during-migration |
| difference-in-female-and-male-life-expectancy-at-age-45 | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.912 | 0.395 | 0.912 | 0.395 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/difference-in-female-and-male-life-expectancy-at-age-45 |
| diphtheria-cases-in-the-united-states | held-out | yes | ok | yes | ok | 1 | 1 | 0.651 | 0.965 | 0.651 | 0.965 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/diphtheria-cases-in-the-united-states |
| fatal-airliner-accidents-per-million-flights | held-out | yes | ok | yes | ok | 1 | 1 | 0.232 | 1.000 | 0.232 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fatal-airliner-accidents-per-million-flights |
| fish-catch-uk | held-out | yes | ok | yes | ok | 2 | 2 | 0.595 | 0.960 | 0.595 | 0.960 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fish-catch-uk |
| global-commodity-prices-19602019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.285 | 1.000 | 0.285 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-commodity-prices-19602019 |
| global-death-rate-in-violent-political-conflicts-over-the-long-run | held-out | no | no_calibration | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-death-rate-in-violent-political-conflicts-over-the-long-run |
| global-smallpox-cases | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 6.145 | 0.655 | 6.145 | 0.655 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-smallpox-cases |
| growth-of-global-trade | held-out | yes | ok | yes | ok | 1 | 1 | 0.159 | 1.000 | 0.159 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/growth-of-global-trade |
| heat-wave-index-usa | held-out | yes | ok | yes | ok | 1 | 1 | 1.035 | 0.910 | 1.035 | 0.910 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/heat-wave-index-usa |
| hepb3-number-unvaccinated | held-out | yes | ok | yes | ok | 1 | 1 | 0.171 | 1.000 | 0.171 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/hepb3-number-unvaccinated |
| india-government-debt-as-a-percentage-of-gdp-19802019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.216 | 1.000 | 0.216 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/india-government-debt-as-a-percentage-of-gdp-19802019 |
| indian-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.112 | 1.000 | 0.112 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/indian-rhinos |
| javan-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.161 | 1.000 | 0.161 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/javan-rhinos |
| labor-force-participation-rate-of-men-65-years-and-older-in-the-usa | held-out | yes | ok | yes | ok | 1 | 1 | 0.140 | 1.000 | 0.140 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/labor-force-participation-rate-of-men-65-years-and-older-in-the-usa |
| land-natural-share | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.100 | 0.725 | 0.100 | 0.730 | 9 | CC BY 4.0 | https://ourworldindata.org/grapher/land-natural-share |
| land-use-agriculture-longterm | held-out | yes | ok | yes | ok | 1 | 1 | 0.073 | 1.000 | 0.073 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/land-use-agriculture-longterm |
| long-term-cod-catch | held-out | yes | ok | yes | ok | 1 | 1 | 0.733 | 0.905 | 0.733 | 0.905 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/long-term-cod-catch |
| maize-production | held-out | no | x_coverage | no | x_coverage | 5 | 5 | 1.430 | 0.585 | 1.430 | 0.585 | 3 | CC BY 4.0 | https://ourworldindata.org/grapher/maize-production |
| marriage-rate-per-1000-inhabitants | held-out | no | series_count | no | series_count | 5 | 4 | 3.863 | 0.710 | 3.863 | 0.710 | 4 | CC BY 4.0 | https://ourworldindata.org/grapher/marriage-rate-per-1000-inhabitants |
| material-footprint-per-capita | held-out | yes | ok | yes | ok | 1 | 1 | 0.063 | 1.000 | 0.063 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/material-footprint-per-capita |
| mention-of-the-word-capitalism-in-new-york-times-articles | held-out | yes | ok | yes | ok | 1 | 1 | 1.163 | 0.900 | 1.163 | 0.900 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/mention-of-the-word-capitalism-in-new-york-times-articles |
| microplastics-in-ocean | held-out | no | series_count | no | series_count | 3 | 2 | 0.285 | 0.175 | 0.285 | 0.175 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/microplastics-in-ocean |
| new-reported-cases-tetanus | held-out | yes | ok | yes | ok | 1 | 1 | 0.206 | 1.000 | 0.206 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/new-reported-cases-tetanus |
| nitrous-oxide-long | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 5.186 | 0.375 | 5.186 | 0.375 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/nitrous-oxide-long |
| northern-white-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.150 | 1.000 | 0.150 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/northern-white-rhinos |
| number-of-child-deaths-unwpp | held-out | yes | ok | yes | ok | 1 | 1 | 0.131 | 1.000 | 0.131 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-child-deaths-unwpp |
| number-of-natural-disaster-events | held-out | yes | ok | yes | ok | 1 | 1 | 0.338 | 1.000 | 0.338 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-natural-disaster-events |
| number-un-peacekeeping-missions | held-out | yes | ok | yes | ok | 1 | 1 | 1.243 | 0.975 | 1.243 | 0.975 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-un-peacekeeping-missions |
| ozone-depleting-substances-index | held-out | yes | ok | yes | ok | 1 | 1 | 0.184 | 1.000 | 0.184 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substances-index |
| percentage-of-persons-without-health-insurance-coverage-us | held-out | yes | ok | yes | ok | 1 | 1 | 0.129 | 1.000 | 0.129 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/percentage-of-persons-without-health-insurance-coverage-us |
| population-growth-rate | held-out | yes | ok | yes | ok | 1 | 1 | 0.816 | 0.970 | 0.816 | 0.970 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/population-growth-rate |
| prevalence-of-undernourishment-in-developing-countries-since-1970 | held-out | yes | ok | yes | ok | 1 | 1 | 0.099 | 1.000 | 0.099 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/prevalence-of-undernourishment-in-developing-countries-since-1970 |
| rubella-cases-in-the-united-states | held-out | yes | ok | yes | ok | 1 | 1 | 0.560 | 0.945 | 0.560 | 0.945 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/rubella-cases-in-the-united-states |
| same-sex-marriage-country-count | held-out | yes | ok | yes | ok | 1 | 1 | 0.111 | 1.000 | 0.111 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/same-sex-marriage-country-count |
| share-of-agriculture-in-total-employment | held-out | yes | ok | yes | ok | 1 | 1 | 0.106 | 1.000 | 0.106 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-agriculture-in-total-employment |
| southern-white-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.153 | 1.000 | 0.153 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/southern-white-rhinos |
| the-number-of-reported-paralytic-polio-cases | held-out | yes | ok | yes | ok | 1 | 1 | 0.236 | 1.000 | 0.236 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases |
| tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv | held-out | yes | ok | yes | ok | 1 | 1 | 0.081 | 1.000 | 0.081 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv |
| uk-gdp-growth-19572016 | held-out | yes | ok | yes | ok | 1 | 1 | 0.785 | 0.970 | 0.785 | 0.970 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-gdp-growth-19572016 |
| uk-government-debt-as-a-percentage-of-gdp-17272016 | held-out | yes | ok | yes | ok | 1 | 1 | 0.684 | 0.970 | 0.684 | 0.970 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-government-debt-as-a-percentage-of-gdp-17272016 |
| uk-inflation-rate-19892019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.229 | 1.000 | 0.229 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-inflation-rate-19892019 |
| wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 | held-out | yes | ok | yes | ok | 1 | 1 | 0.266 | 1.000 | 0.266 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 |
| wages-relative-to-the-cost-of-capital | held-out | yes | ok | yes | ok | 2 | 2 | 0.152 | 1.000 | 0.152 | 1.000 | 1 | CC BY 4.0 | https://ourworldindata.org/grapher/wages-relative-to-the-cost-of-capital |
| what-percentage-of-the-us-public-approves-of-working-wives | held-out | yes | ok | yes | ok | 1 | 1 | 0.163 | 1.000 | 0.163 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/what-percentage-of-the-us-public-approves-of-working-wives |
| wildlife-exports | held-out | no | series_count | no | series_count | 6 | 5 | 37.534 | 0.000 | 37.845 | 0.000 | 9 | CC BY 4.0 | https://ourworldindata.org/grapher/wildlife-exports |
