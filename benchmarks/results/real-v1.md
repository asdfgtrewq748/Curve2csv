# Real-figure results (owid-grapher-v1)

Commit `bb6f43955ea8eed74694fedcb49ed6e7e64664e1`. Python 3.12.3.

A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90. Flagged points are excluded before scoring.

| split | n | correct | accuracy |
|---|---:|---:|---:|
| dev | 49 | 31 | 63.27% |
| held-out | 61 | 39 | 63.93% |
| all | 110 | 70 | 63.64% |

Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:

- dev: n_fit=2, median |Δslope|/|slope|=0.016, median |Δintercept|/range=0.899
- held-out: n_fit=2, median |Δslope|/|slope|=0.005, median |Δintercept|/range=0.052
- all: n_fit=4, median |Δslope|/|slope|=0.009, median |Δintercept|/range=0.152

## Per figure

| slug | split | correct | reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | slope rel err | intercept / range | license | url |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| air-passengers-per-fatality | dev | no | nrmse_and_coverage | 1 | 1 | 6.741 | 0.520 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/air-passengers-per-fatality |
| annual-fish-catch-taxa | held-out | no | x_coverage | 5 | 5 | 0.405 | 0.165 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-fish-catch-taxa |
| annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar | held-out | yes | ok | 1 | 1 | 0.222 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar |
| annual-patents-invention-united-states-1790 | held-out | yes | ok | 1 | 1 | 0.561 | 0.960 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-patents-invention-united-states-1790 |
| arable-land-pin | held-out | yes | ok | 1 | 1 | 0.111 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/arable-land-pin |
| arctic-sea-ice-coverage-19352014 | dev | yes | ok | 1 | 1 | 0.395 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/arctic-sea-ice-coverage-19352014 |
| aviation-fatalities-per-million-passengers | dev | yes | ok | 1 | 1 | 0.274 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/aviation-fatalities-per-million-passengers |
| banana-yields | dev | no | x_coverage | 3 | 3 | 0.522 | 0.075 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/banana-yields |
| bean-yields | dev | no | x_coverage | 4 | 4 | 0.171 | 0.145 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/bean-yields |
| biomass-fish-stocks-taxa | held-out | yes | ok | 1 | 1 | 0.108 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/biomass-fish-stocks-taxa |
| breast-cancer-death-rate-in-women | held-out | no | x_coverage | 6 | 6 | 0.219 | 0.130 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/breast-cancer-death-rate-in-women |
| cases-of-paralytic-polio-from-wild-polioviruses | held-out | no | no_calibration | 5 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cases-of-paralytic-polio-from-wild-polioviruses |
| cashew-nut-yields | held-out | no | series_count | 4 | 3 | 7.618 | 0.005 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cashew-nut-yields |
| cholera-case-fatality-rate | held-out | yes | ok | 1 | 1 | 0.632 | 0.970 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cholera-case-fatality-rate |
| co2-long-term-concentration | held-out | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/co2-long-term-concentration |
| coal-output-per-worker-in-the-united-kingdom | held-out | yes | ok | 1 | 1 | 0.559 | 0.975 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/coal-output-per-worker-in-the-united-kingdom |
| cohort-fertility-rate | dev | no | x_coverage | 6 | 6 | 0.274 | 0.145 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cohort-fertility-rate |
| computer-chess-ability | dev | yes | ok | 1 | 1 | 0.123 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/computer-chess-ability |
| cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 | held-out | yes | ok | 1 | 1 | 0.491 | 0.975 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 |
| countries-with-a-signed-bilateral-investment-treaty | held-out | yes | ok | 2 | 2 | 0.255 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-a-signed-bilateral-investment-treaty |
| countries-with-an-inforce-bilateral-investment-treaty | held-out | yes | ok | 2 | 2 | 0.372 | 0.955 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-an-inforce-bilateral-investment-treaty |
| crude-death-rate-hmd | dev | no | series_count | 5 | 4 | 2.998 | 0.090 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/crude-death-rate-hmd |
| cumulative-space-visits | held-out | no | x_coverage | 4 | 4 | 0.614 | 0.075 | 0.006 | 0.042 | CC BY 4.0 | https://ourworldindata.org/grapher/cumulative-space-visits |
| daily-per-capita-caloric-supply | dev | yes | ok | 1 | 1 | 0.198 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/daily-per-capita-caloric-supply |
| deaths-and-disappearances-during-migration | held-out | yes | ok | 1 | 1 | 0.257 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-and-disappearances-during-migration |
| deaths-from-aids-un | dev | yes | ok | 1 | 1 | 1.414 | 0.910 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-aids-un |
| deaths-from-smallpox-in-london | dev | no | nrmse_and_coverage | 1 | 1 | 2.808 | 0.630 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-smallpox-in-london |
| difference-in-female-and-male-life-expectancy-at-age-45 | held-out | no | x_coverage | 4 | 4 | 0.943 | 0.030 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/difference-in-female-and-male-life-expectancy-at-age-45 |
| different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk | dev | yes | ok | 2 | 2 | 0.097 | 0.910 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk |
| diphtheria-cases-in-the-united-states | held-out | no | nrmse_and_coverage | 1 | 1 | 3.646 | 0.835 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/diphtheria-cases-in-the-united-states |
| electric-car-stocks | dev | no | x_coverage | 4 | 4 | 0.600 | 0.050 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/electric-car-stocks |
| electricity-air-conditioning | dev | yes | ok | 1 | 1 | 0.079 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/electricity-air-conditioning |
| employment-in-the-coal-industry-in-the-united-kingdom | dev | yes | ok | 1 | 1 | 0.518 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/employment-in-the-coal-industry-in-the-united-kingdom |
| fatal-airliner-accidents-per-million-flights | held-out | yes | ok | 1 | 1 | 0.232 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fatal-airliner-accidents-per-million-flights |
| fatality-rates-due-to-lightning-in-the-us | dev | yes | ok | 1 | 1 | 0.498 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fatality-rates-due-to-lightning-in-the-us |
| fertilizer-total-use | dev | yes | ok | 1 | 1 | 0.146 | 0.945 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fertilizer-total-use |
| fish-catch-uk | held-out | yes | ok | 2 | 2 | 0.592 | 0.955 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fish-catch-uk |
| fish-discards | dev | yes | ok | 1 | 1 | 0.208 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fish-discards |
| foreign-born-population-of-the-united-states | dev | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/foreign-born-population-of-the-united-states |
| global-commodity-prices-19602019 | held-out | yes | ok | 1 | 1 | 0.285 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-commodity-prices-19602019 |
| global-death-rate-in-violent-political-conflicts-over-the-long-run | held-out | no | nrmse_and_coverage | 1 | 1 | 13.836 | 0.230 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-death-rate-in-violent-political-conflicts-over-the-long-run |
| global-deaths-in-violent-political-conflicts-over-the-long-run | dev | no | nrmse_and_coverage | 1 | 1 | 10.810 | 0.240 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-deaths-in-violent-political-conflicts-over-the-long-run |
| global-plastics-production | dev | yes | ok | 1 | 1 | 0.114 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-plastics-production |
| global-smallpox-cases | held-out | no | nrmse_and_coverage | 1 | 1 | 6.251 | 0.660 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-smallpox-cases |
| growth-of-global-trade | held-out | no | x_coverage | 1 | 1 | 1.527 | 0.870 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/growth-of-global-trade |
| heat-wave-index-usa | held-out | yes | ok | 1 | 1 | 1.304 | 0.905 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/heat-wave-index-usa |
| hepb3-number-unvaccinated | held-out | yes | ok | 1 | 1 | 0.171 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/hepb3-number-unvaccinated |
| homicide-rates-across-western-europe | dev | no | nrmse_and_coverage | 5 | 5 | 9.796 | 0.035 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/homicide-rates-across-western-europe |
| incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 | dev | yes | ok | 1 | 1 | 0.097 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 |
| india-government-debt-as-a-percentage-of-gdp-19802019 | held-out | yes | ok | 1 | 1 | 0.991 | 0.905 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/india-government-debt-as-a-percentage-of-gdp-19802019 |
| indian-rhinos | held-out | yes | ok | 1 | 1 | 0.112 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/indian-rhinos |
| international-capital-flows | dev | yes | ok | 1 | 1 | 0.327 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/international-capital-flows |
| interpersonal-trust-in-the-us | dev | yes | ok | 1 | 1 | 0.186 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/interpersonal-trust-in-the-us |
| javan-rhinos | held-out | yes | ok | 1 | 1 | 0.161 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/javan-rhinos |
| labor-force-participation-rate-of-men-65-years-and-older-in-the-usa | held-out | yes | ok | 1 | 1 | 0.202 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-force-participation-rate-of-men-65-years-and-older-in-the-usa |
| labor-productivity-agriculture-sweden | dev | yes | ok | 1 | 1 | 0.259 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-agriculture-sweden |
| labor-productivity-per-hour | dev | yes | ok | 1 | 1 | 0.142 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-per-hour |
| land-natural-share | held-out | no | x_coverage | 4 | 4 | 0.208 | 0.115 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/land-natural-share |
| land-use-agriculture-longterm | held-out | yes | ok | 1 | 1 | 0.073 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/land-use-agriculture-longterm |
| long-term-cod-catch | held-out | yes | ok | 1 | 1 | 0.858 | 0.915 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/long-term-cod-catch |
| macroplastics-in-ocean | dev | no | series_count | 3 | 2 | 0.129 | 0.245 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/macroplastics-in-ocean |
| maize-production | held-out | no | x_coverage | 5 | 5 | 1.430 | 0.125 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/maize-production |
| marriage-rate-per-1000-inhabitants | held-out | no | series_count | 5 | 4 | 1.416 | 0.330 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/marriage-rate-per-1000-inhabitants |
| material-footprint-per-capita | held-out | yes | ok | 1 | 1 | 0.063 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/material-footprint-per-capita |
| mention-of-the-word-capitalism-in-new-york-times-articles | held-out | no | nrmse_and_coverage | 1 | 1 | 6.133 | 0.265 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/mention-of-the-word-capitalism-in-new-york-times-articles |
| microplastics-in-ocean | held-out | no | series_count | 3 | 2 | 0.314 | 0.165 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/microplastics-in-ocean |
| natural-resource-rents | dev | yes | ok | 1 | 1 | 0.328 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/natural-resource-rents |
| new-reported-cases-tetanus | held-out | yes | ok | 1 | 1 | 0.207 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/new-reported-cases-tetanus |
| nitrous-oxide-long | held-out | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/nitrous-oxide-long |
| northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c | dev | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c |
| northern-white-rhinos | held-out | yes | ok | 1 | 1 | 0.432 | 0.985 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/northern-white-rhinos |
| number-of-child-deaths-unwpp | held-out | yes | ok | 1 | 1 | 0.128 | 1.000 | 0.003 | 0.061 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-child-deaths-unwpp |
| number-of-countries-having-implemented-a-vat | dev | yes | ok | 1 | 1 | 0.085 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-countries-having-implemented-a-vat |
| number-of-natural-disaster-events | held-out | yes | ok | 1 | 1 | 0.489 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-natural-disaster-events |
| number-of-patents-through-the-industrial-revolution | dev | no | nrmse_and_coverage | 3 | 3 | 4.023 | 0.050 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-patents-through-the-industrial-revolution |
| number-un-peacekeeping-missions | held-out | yes | ok | 1 | 1 | 1.243 | 0.975 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-un-peacekeeping-missions |
| ozone-depleting-substance-emissions | dev | yes | ok | 2 | 2 | 0.140 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substance-emissions |
| ozone-depleting-substances-index | held-out | yes | ok | 1 | 1 | 0.184 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substances-index |
| palm-oil-production | dev | yes | ok | 1 | 1 | 0.159 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/palm-oil-production |
| percentage-of-persons-without-health-insurance-coverage-us | held-out | yes | ok | 1 | 1 | 0.129 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/percentage-of-persons-without-health-insurance-coverage-us |
| population-growth-rate | held-out | yes | ok | 1 | 1 | 1.139 | 0.910 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/population-growth-rate |
| population-of-england-millennium | dev | yes | ok | 1 | 1 | 0.154 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/population-of-england-millennium |
| population-unwpp | dev | no | x_coverage | 3 | 3 | 0.114 | 0.200 | 0.013 | 0.242 | CC BY 4.0 | https://ourworldindata.org/grapher/population-unwpp |
| prevalence-of-undernourishment-in-developing-countries-since-1970 | held-out | yes | ok | 1 | 1 | 0.099 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/prevalence-of-undernourishment-in-developing-countries-since-1970 |
| public-trust-in-government | dev | yes | ok | 1 | 1 | 0.589 | 0.980 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/public-trust-in-government |
| reported-share-of-people-experiencing-homelessness | dev | yes | ok | 1 | 1 | 0.069 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/reported-share-of-people-experiencing-homelessness |
| rubella-cases-in-the-united-states | held-out | no | nrmse_and_coverage | 1 | 1 | 3.803 | 0.800 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/rubella-cases-in-the-united-states |
| same-sex-marriage-country-count | held-out | no | x_coverage | 1 | 1 | 1.141 | 0.530 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/same-sex-marriage-country-count |
| share-of-agriculture-in-total-employment | held-out | yes | ok | 1 | 1 | 0.106 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-agriculture-in-total-employment |
| share-of-the-workforce-employed-in-the-coal-industry-united-kingdom | dev | yes | ok | 1 | 1 | 0.409 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-the-workforce-employed-in-the-coal-industry-united-kingdom |
| southern-white-rhinos | held-out | yes | ok | 1 | 1 | 0.414 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/southern-white-rhinos |
| stomach-cancer-death-rate | dev | no | x_coverage | 6 | 6 | 0.170 | 0.100 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stomach-cancer-death-rate |
| stratospheric-chorine-concentrations | dev | no | x_coverage | 3 | 3 | 0.460 | 0.160 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-chorine-concentrations |
| stratospheric-ozone-concentration-projections | dev | no | nrmse_and_coverage | 3 | 3 | 6.707 | 0.100 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-ozone-concentration-projections |
| supercomputer-power-flops | dev | yes | ok | 1 | 1 | 1.065 | 0.925 | 0.019 | 1.556 | CC BY 4.0 | https://ourworldindata.org/grapher/supercomputer-power-flops |
| the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 | dev | yes | ok | 1 | 1 | 1.207 | 0.950 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 |
| the-growth-of-government-in-the-uk | dev | yes | ok | 1 | 1 | 0.522 | 0.965 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-growth-of-government-in-the-uk |
| the-number-of-reported-paralytic-polio-cases | held-out | yes | ok | 1 | 1 | 0.236 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases |
| total-agricultural-land-use-per-person | dev | yes | ok | 1 | 1 | 0.127 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/total-agricultural-land-use-per-person |
| tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv | held-out | yes | ok | 1 | 1 | 0.081 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv |
| uk-gdp-growth-19572016 | held-out | no | nrmse_and_coverage | 1 | 1 | 7.240 | 0.465 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-gdp-growth-19572016 |
| uk-government-debt-as-a-percentage-of-gdp-17272016 | held-out | yes | ok | 1 | 1 | 0.736 | 0.965 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-government-debt-as-a-percentage-of-gdp-17272016 |
| uk-inflation-rate-19892019 | held-out | yes | ok | 1 | 1 | 0.229 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-inflation-rate-19892019 |
| uk-unemployment-rate-19712017 | dev | yes | ok | 1 | 1 | 0.312 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-unemployment-rate-19712017 |
| un-projection-of-annual-infant-deaths | dev | yes | ok | 1 | 1 | 0.093 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/un-projection-of-annual-infant-deaths |
| wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 | held-out | no | nrmse_and_coverage | 1 | 1 | 2.629 | 0.700 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 |
| wages-relative-to-the-cost-of-capital | held-out | yes | ok | 2 | 2 | 0.154 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wages-relative-to-the-cost-of-capital |
| what-percentage-of-the-us-public-approves-of-working-wives | held-out | yes | ok | 1 | 1 | 0.163 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/what-percentage-of-the-us-public-approves-of-working-wives |
| wildlife-exports | held-out | no | series_count | 6 | 5 | 30.803 | 0.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wildlife-exports |
| working-hours-uk-millennium | dev | no | nrmse_and_coverage | 1 | 1 | 3.749 | 0.730 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/working-hours-uk-millennium |
