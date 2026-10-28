# Real-figure results (owid-grapher-v1)

Commit `c5679415f2c09c9e81422e58dc846e0c4d8150be`. Python 3.12.3.

Strict scoring drops every flagged point, including occlusion bridges. With-bridge scoring keeps points flagged `INTERPOLATED` and still drops every other flag. A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90.

| split | n | strict | strict accuracy | with-bridge | with-bridge accuracy |
|---|---:|---:|---:|---:|---:|
| dev | 49 | 32 | 65.31% | 32 | 65.31% |
| held-out | 61 | 39 | 63.93% | 39 | 63.93% |
| all | 110 | 71 | 64.55% | 71 | 64.55% |

Mean CPU time 0.984s/image. Bridged points: 72.

Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:

- dev: n_fit=2, median |Δslope|/|slope|=0.011, median |Δintercept|/range=0.809
- held-out: n_fit=2, median |Δslope|/|slope|=0.009, median |Δintercept|/range=0.080
- all: n_fit=4, median |Δslope|/|slope|=0.009, median |Δintercept|/range=0.080

## Per figure

| slug | split | strict | reason | bridge | bridge reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | bridge NRMSE % | bridge x-coverage | bridged | license | url |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| air-passengers-per-fatality | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 6.820 | 0.520 | 6.820 | 0.520 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/air-passengers-per-fatality |
| annual-fish-catch-taxa | held-out | no | x_coverage | no | x_coverage | 5 | 5 | 0.397 | 0.635 | 0.418 | 0.635 | 17 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-fish-catch-taxa |
| annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar | held-out | yes | ok | yes | ok | 1 | 1 | 0.222 | 0.995 | 0.222 | 0.995 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar |
| annual-patents-invention-united-states-1790 | held-out | yes | ok | yes | ok | 1 | 1 | 0.561 | 0.960 | 0.561 | 0.960 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/annual-patents-invention-united-states-1790 |
| arable-land-pin | held-out | yes | ok | yes | ok | 1 | 1 | 0.111 | 1.000 | 0.111 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/arable-land-pin |
| arctic-sea-ice-coverage-19352014 | dev | yes | ok | yes | ok | 1 | 1 | 0.395 | 1.000 | 0.395 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/arctic-sea-ice-coverage-19352014 |
| aviation-fatalities-per-million-passengers | dev | yes | ok | yes | ok | 1 | 1 | 0.274 | 1.000 | 0.274 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/aviation-fatalities-per-million-passengers |
| banana-yields | dev | no | x_coverage | no | x_coverage | 3 | 3 | 0.494 | 0.555 | 0.494 | 0.555 | 2 | CC BY 4.0 | https://ourworldindata.org/grapher/banana-yields |
| bean-yields | dev | no | x_coverage | no | x_coverage | 4 | 4 | 0.171 | 0.720 | 0.171 | 0.725 | 4 | CC BY 4.0 | https://ourworldindata.org/grapher/bean-yields |
| biomass-fish-stocks-taxa | held-out | yes | ok | yes | ok | 1 | 1 | 0.108 | 1.000 | 0.108 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/biomass-fish-stocks-taxa |
| breast-cancer-death-rate-in-women | held-out | no | x_coverage | no | x_coverage | 6 | 6 | 0.161 | 0.620 | 0.161 | 0.620 | 3 | CC BY 4.0 | https://ourworldindata.org/grapher/breast-cancer-death-rate-in-women |
| cases-of-paralytic-polio-from-wild-polioviruses | held-out | no | no_calibration | no | no_calibration | 5 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cases-of-paralytic-polio-from-wild-polioviruses |
| cashew-nut-yields | held-out | no | series_count | no | series_count | 4 | 3 | 7.618 | 0.005 | 7.618 | 0.005 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cashew-nut-yields |
| cholera-case-fatality-rate | held-out | yes | ok | yes | ok | 1 | 1 | 0.661 | 0.950 | 0.661 | 0.950 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cholera-case-fatality-rate |
| co2-long-term-concentration | held-out | no | no_calibration | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/co2-long-term-concentration |
| coal-output-per-worker-in-the-united-kingdom | held-out | yes | ok | yes | ok | 1 | 1 | 0.369 | 0.965 | 0.369 | 0.965 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/coal-output-per-worker-in-the-united-kingdom |
| cohort-fertility-rate | dev | no | x_coverage | no | x_coverage | 6 | 6 | 0.245 | 0.645 | 0.245 | 0.645 | 3 | CC BY 4.0 | https://ourworldindata.org/grapher/cohort-fertility-rate |
| computer-chess-ability | dev | yes | ok | yes | ok | 1 | 1 | 0.123 | 1.000 | 0.123 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/computer-chess-ability |
| cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 | held-out | yes | ok | yes | ok | 1 | 1 | 0.491 | 0.975 | 0.491 | 0.975 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 |
| countries-with-a-signed-bilateral-investment-treaty | held-out | yes | ok | yes | ok | 2 | 2 | 0.255 | 1.000 | 0.255 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-a-signed-bilateral-investment-treaty |
| countries-with-an-inforce-bilateral-investment-treaty | held-out | yes | ok | yes | ok | 2 | 2 | 0.372 | 0.955 | 0.372 | 0.955 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-an-inforce-bilateral-investment-treaty |
| crude-death-rate-hmd | dev | no | x_coverage | no | x_coverage | 5 | 5 | 2.712 | 0.090 | 2.712 | 0.090 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/crude-death-rate-hmd |
| cumulative-space-visits | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.597 | 0.855 | 0.597 | 0.855 | 5 | CC BY 4.0 | https://ourworldindata.org/grapher/cumulative-space-visits |
| daily-per-capita-caloric-supply | dev | yes | ok | yes | ok | 1 | 1 | 0.348 | 0.990 | 0.348 | 0.990 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/daily-per-capita-caloric-supply |
| deaths-and-disappearances-during-migration | held-out | yes | ok | yes | ok | 1 | 1 | 0.257 | 1.000 | 0.257 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-and-disappearances-during-migration |
| deaths-from-aids-un | dev | yes | ok | yes | ok | 1 | 1 | 1.414 | 0.910 | 1.414 | 0.910 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-aids-un |
| deaths-from-smallpox-in-london | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 3.039 | 0.500 | 3.039 | 0.500 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-smallpox-in-london |
| difference-in-female-and-male-life-expectancy-at-age-45 | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.943 | 0.390 | 0.943 | 0.390 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/difference-in-female-and-male-life-expectancy-at-age-45 |
| different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk | dev | yes | ok | yes | ok | 2 | 2 | 0.106 | 0.935 | 0.106 | 0.935 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk |
| diphtheria-cases-in-the-united-states | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 3.646 | 0.835 | 3.646 | 0.835 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/diphtheria-cases-in-the-united-states |
| electric-car-stocks | dev | no | x_coverage | no | x_coverage | 4 | 4 | 0.563 | 0.380 | 0.563 | 0.380 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/electric-car-stocks |
| electricity-air-conditioning | dev | yes | ok | yes | ok | 1 | 1 | 0.079 | 1.000 | 0.079 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/electricity-air-conditioning |
| employment-in-the-coal-industry-in-the-united-kingdom | dev | yes | ok | yes | ok | 1 | 1 | 0.518 | 0.990 | 0.518 | 0.990 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/employment-in-the-coal-industry-in-the-united-kingdom |
| fatal-airliner-accidents-per-million-flights | held-out | yes | ok | yes | ok | 1 | 1 | 0.232 | 1.000 | 0.232 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fatal-airliner-accidents-per-million-flights |
| fatality-rates-due-to-lightning-in-the-us | dev | yes | ok | yes | ok | 1 | 1 | 0.466 | 0.995 | 0.466 | 0.995 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fatality-rates-due-to-lightning-in-the-us |
| fertilizer-total-use | dev | yes | ok | yes | ok | 1 | 1 | 0.146 | 0.945 | 0.146 | 0.945 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fertilizer-total-use |
| fish-catch-uk | held-out | yes | ok | yes | ok | 2 | 2 | 0.595 | 0.960 | 0.595 | 0.960 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fish-catch-uk |
| fish-discards | dev | yes | ok | yes | ok | 1 | 1 | 0.208 | 1.000 | 0.208 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/fish-discards |
| foreign-born-population-of-the-united-states | dev | no | no_calibration | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/foreign-born-population-of-the-united-states |
| global-commodity-prices-19602019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.285 | 1.000 | 0.285 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-commodity-prices-19602019 |
| global-death-rate-in-violent-political-conflicts-over-the-long-run | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 12.627 | 0.230 | 12.627 | 0.230 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-death-rate-in-violent-political-conflicts-over-the-long-run |
| global-deaths-in-violent-political-conflicts-over-the-long-run | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 10.657 | 0.240 | 10.657 | 0.240 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-deaths-in-violent-political-conflicts-over-the-long-run |
| global-plastics-production | dev | yes | ok | yes | ok | 1 | 1 | 0.114 | 0.995 | 0.114 | 0.995 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-plastics-production |
| global-smallpox-cases | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 6.145 | 0.655 | 6.145 | 0.655 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/global-smallpox-cases |
| growth-of-global-trade | held-out | no | x_coverage | no | x_coverage | 1 | 1 | 1.527 | 0.870 | 1.527 | 0.870 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/growth-of-global-trade |
| heat-wave-index-usa | held-out | yes | ok | yes | ok | 1 | 1 | 1.035 | 0.910 | 1.035 | 0.910 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/heat-wave-index-usa |
| hepb3-number-unvaccinated | held-out | yes | ok | yes | ok | 1 | 1 | 0.171 | 1.000 | 0.171 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/hepb3-number-unvaccinated |
| homicide-rates-across-western-europe | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 5 | 5 | 9.796 | 0.385 | 9.796 | 0.385 | 2 | CC BY 4.0 | https://ourworldindata.org/grapher/homicide-rates-across-western-europe |
| incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 | dev | yes | ok | yes | ok | 1 | 1 | 0.097 | 1.000 | 0.097 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 |
| india-government-debt-as-a-percentage-of-gdp-19802019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.991 | 0.905 | 0.991 | 0.905 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/india-government-debt-as-a-percentage-of-gdp-19802019 |
| indian-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.112 | 1.000 | 0.112 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/indian-rhinos |
| international-capital-flows | dev | yes | ok | yes | ok | 1 | 1 | 0.327 | 1.000 | 0.327 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/international-capital-flows |
| interpersonal-trust-in-the-us | dev | yes | ok | yes | ok | 1 | 1 | 0.186 | 1.000 | 0.186 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/interpersonal-trust-in-the-us |
| javan-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.161 | 1.000 | 0.161 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/javan-rhinos |
| labor-force-participation-rate-of-men-65-years-and-older-in-the-usa | held-out | yes | ok | yes | ok | 1 | 1 | 0.202 | 0.995 | 0.202 | 0.995 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/labor-force-participation-rate-of-men-65-years-and-older-in-the-usa |
| labor-productivity-agriculture-sweden | dev | yes | ok | yes | ok | 1 | 1 | 0.259 | 1.000 | 0.259 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-agriculture-sweden |
| labor-productivity-per-hour | dev | yes | ok | yes | ok | 1 | 1 | 0.142 | 1.000 | 0.142 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-per-hour |
| land-natural-share | held-out | no | x_coverage | no | x_coverage | 4 | 4 | 0.100 | 0.725 | 0.100 | 0.730 | 9 | CC BY 4.0 | https://ourworldindata.org/grapher/land-natural-share |
| land-use-agriculture-longterm | held-out | yes | ok | yes | ok | 1 | 1 | 0.073 | 1.000 | 0.073 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/land-use-agriculture-longterm |
| long-term-cod-catch | held-out | yes | ok | yes | ok | 1 | 1 | 0.731 | 0.905 | 0.731 | 0.905 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/long-term-cod-catch |
| macroplastics-in-ocean | dev | no | series_count | no | series_count | 3 | 2 | 0.129 | 0.255 | 0.129 | 0.255 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/macroplastics-in-ocean |
| maize-production | held-out | no | x_coverage | no | x_coverage | 5 | 5 | 1.430 | 0.585 | 1.430 | 0.585 | 3 | CC BY 4.0 | https://ourworldindata.org/grapher/maize-production |
| marriage-rate-per-1000-inhabitants | held-out | no | series_count | no | series_count | 5 | 4 | 3.867 | 0.710 | 3.867 | 0.710 | 4 | CC BY 4.0 | https://ourworldindata.org/grapher/marriage-rate-per-1000-inhabitants |
| material-footprint-per-capita | held-out | yes | ok | yes | ok | 1 | 1 | 0.063 | 1.000 | 0.063 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/material-footprint-per-capita |
| mention-of-the-word-capitalism-in-new-york-times-articles | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 5.982 | 0.255 | 5.982 | 0.255 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/mention-of-the-word-capitalism-in-new-york-times-articles |
| microplastics-in-ocean | held-out | no | series_count | no | series_count | 3 | 2 | 0.285 | 0.175 | 0.285 | 0.175 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/microplastics-in-ocean |
| natural-resource-rents | dev | yes | ok | yes | ok | 1 | 1 | 0.328 | 1.000 | 0.328 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/natural-resource-rents |
| new-reported-cases-tetanus | held-out | yes | ok | yes | ok | 1 | 1 | 0.207 | 1.000 | 0.207 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/new-reported-cases-tetanus |
| nitrous-oxide-long | held-out | no | no_calibration | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/nitrous-oxide-long |
| northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c | dev | no | no_calibration | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c |
| northern-white-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.432 | 0.985 | 0.432 | 0.985 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/northern-white-rhinos |
| number-of-child-deaths-unwpp | held-out | yes | ok | yes | ok | 1 | 1 | 0.128 | 1.000 | 0.128 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-child-deaths-unwpp |
| number-of-countries-having-implemented-a-vat | dev | yes | ok | yes | ok | 1 | 1 | 0.085 | 1.000 | 0.085 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-countries-having-implemented-a-vat |
| number-of-natural-disaster-events | held-out | yes | ok | yes | ok | 1 | 1 | 0.338 | 1.000 | 0.338 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-natural-disaster-events |
| number-of-patents-through-the-industrial-revolution | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 3 | 3 | 3.750 | 0.325 | 3.750 | 0.325 | 8 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-patents-through-the-industrial-revolution |
| number-un-peacekeeping-missions | held-out | yes | ok | yes | ok | 1 | 1 | 1.243 | 0.975 | 1.243 | 0.975 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/number-un-peacekeeping-missions |
| ozone-depleting-substance-emissions | dev | yes | ok | yes | ok | 2 | 2 | 0.140 | 1.000 | 0.140 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substance-emissions |
| ozone-depleting-substances-index | held-out | yes | ok | yes | ok | 1 | 1 | 0.184 | 1.000 | 0.184 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substances-index |
| palm-oil-production | dev | yes | ok | yes | ok | 1 | 1 | 0.159 | 1.000 | 0.159 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/palm-oil-production |
| percentage-of-persons-without-health-insurance-coverage-us | held-out | yes | ok | yes | ok | 1 | 1 | 0.129 | 1.000 | 0.129 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/percentage-of-persons-without-health-insurance-coverage-us |
| population-growth-rate | held-out | yes | ok | yes | ok | 1 | 1 | 1.080 | 0.920 | 1.080 | 0.920 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/population-growth-rate |
| population-of-england-millennium | dev | yes | ok | yes | ok | 1 | 1 | 0.154 | 1.000 | 0.154 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/population-of-england-millennium |
| population-unwpp | dev | yes | ok | yes | ok | 3 | 3 | 0.095 | 0.990 | 0.095 | 0.990 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/population-unwpp |
| prevalence-of-undernourishment-in-developing-countries-since-1970 | held-out | yes | ok | yes | ok | 1 | 1 | 0.099 | 1.000 | 0.099 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/prevalence-of-undernourishment-in-developing-countries-since-1970 |
| public-trust-in-government | dev | yes | ok | yes | ok | 1 | 1 | 0.589 | 0.980 | 0.589 | 0.980 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/public-trust-in-government |
| reported-share-of-people-experiencing-homelessness | dev | yes | ok | yes | ok | 1 | 1 | 0.069 | 1.000 | 0.069 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/reported-share-of-people-experiencing-homelessness |
| rubella-cases-in-the-united-states | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 3.047 | 0.800 | 3.047 | 0.800 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/rubella-cases-in-the-united-states |
| same-sex-marriage-country-count | held-out | no | x_coverage | no | x_coverage | 1 | 1 | 1.141 | 0.530 | 1.141 | 0.530 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/same-sex-marriage-country-count |
| share-of-agriculture-in-total-employment | held-out | yes | ok | yes | ok | 1 | 1 | 0.106 | 1.000 | 0.106 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-agriculture-in-total-employment |
| share-of-the-workforce-employed-in-the-coal-industry-united-kingdom | dev | yes | ok | yes | ok | 1 | 1 | 0.419 | 0.995 | 0.419 | 0.995 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-the-workforce-employed-in-the-coal-industry-united-kingdom |
| southern-white-rhinos | held-out | yes | ok | yes | ok | 1 | 1 | 0.414 | 0.990 | 0.414 | 0.990 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/southern-white-rhinos |
| stomach-cancer-death-rate | dev | no | x_coverage | no | x_coverage | 6 | 6 | 0.157 | 0.605 | 0.157 | 0.605 | 1 | CC BY 4.0 | https://ourworldindata.org/grapher/stomach-cancer-death-rate |
| stratospheric-chorine-concentrations | dev | no | x_coverage | no | x_coverage | 3 | 3 | 0.488 | 0.855 | 0.488 | 0.855 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-chorine-concentrations |
| stratospheric-ozone-concentration-projections | dev | no | series_count | no | series_count | 3 | 4 | 1.422 | 0.145 | 1.422 | 0.145 | 1 | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-ozone-concentration-projections |
| supercomputer-power-flops | dev | yes | ok | yes | ok | 1 | 1 | 1.065 | 0.925 | 1.065 | 0.925 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/supercomputer-power-flops |
| the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 | dev | yes | ok | yes | ok | 1 | 1 | 1.051 | 0.950 | 1.051 | 0.950 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 |
| the-growth-of-government-in-the-uk | dev | yes | ok | yes | ok | 1 | 1 | 0.509 | 0.950 | 0.509 | 0.950 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/the-growth-of-government-in-the-uk |
| the-number-of-reported-paralytic-polio-cases | held-out | yes | ok | yes | ok | 1 | 1 | 0.236 | 1.000 | 0.236 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases |
| total-agricultural-land-use-per-person | dev | yes | ok | yes | ok | 1 | 1 | 0.520 | 0.965 | 0.520 | 0.965 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/total-agricultural-land-use-per-person |
| tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv | held-out | yes | ok | yes | ok | 1 | 1 | 0.081 | 1.000 | 0.081 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv |
| uk-gdp-growth-19572016 | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 7.211 | 0.470 | 7.211 | 0.470 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-gdp-growth-19572016 |
| uk-government-debt-as-a-percentage-of-gdp-17272016 | held-out | yes | ok | yes | ok | 1 | 1 | 0.684 | 0.970 | 0.684 | 0.970 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-government-debt-as-a-percentage-of-gdp-17272016 |
| uk-inflation-rate-19892019 | held-out | yes | ok | yes | ok | 1 | 1 | 0.229 | 1.000 | 0.229 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-inflation-rate-19892019 |
| uk-unemployment-rate-19712017 | dev | yes | ok | yes | ok | 1 | 1 | 0.312 | 1.000 | 0.312 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/uk-unemployment-rate-19712017 |
| un-projection-of-annual-infant-deaths | dev | yes | ok | yes | ok | 1 | 1 | 0.093 | 1.000 | 0.093 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/un-projection-of-annual-infant-deaths |
| wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 | held-out | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 2.629 | 0.700 | 2.629 | 0.700 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 |
| wages-relative-to-the-cost-of-capital | held-out | yes | ok | yes | ok | 2 | 2 | 0.155 | 1.000 | 0.155 | 1.000 | 1 | CC BY 4.0 | https://ourworldindata.org/grapher/wages-relative-to-the-cost-of-capital |
| what-percentage-of-the-us-public-approves-of-working-wives | held-out | yes | ok | yes | ok | 1 | 1 | 0.163 | 1.000 | 0.163 | 1.000 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/what-percentage-of-the-us-public-approves-of-working-wives |
| wildlife-exports | held-out | no | series_count | no | series_count | 6 | 5 | 37.534 | 0.000 | 37.845 | 0.000 | 9 | CC BY 4.0 | https://ourworldindata.org/grapher/wildlife-exports |
| working-hours-uk-millennium | dev | no | nrmse_and_coverage | no | nrmse_and_coverage | 1 | 1 | 3.749 | 0.730 | 3.749 | 0.730 | 0 | CC BY 4.0 | https://ourworldindata.org/grapher/working-hours-uk-millennium |
