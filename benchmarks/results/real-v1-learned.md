# Real-figure results (owid-grapher-v1)

Commit `ab65cf976fcf7d7c1450fc9d1fabdade6f127e39`. Python 3.12.3.
Extractor `learned`.

A figure is correct when the predicted series count equals the ground-truth count and every series has NRMSE ≤ 2% of the axis range and x-coverage ≥ 0.90. Flagged points are excluded before scoring.

| split | n | correct | accuracy |
|---|---:|---:|---:|
| dev | 49 | 0 | 0.00% |
| held-out | 61 | 0 | 0.00% |
| all | 110 | 0 | 0.00% |

Parameter error is the worst relative slope error on series whose ground truth is a straight line (R² ≥ 0.98) in axis space. It is not part of the pass rule. Median over figures where a fit applies:

- dev: n_fit=2, median |Δslope|/|slope|=1.881, median |Δintercept|/range=7.344
- held-out: n_fit=2, median |Δslope|/|slope|=0.053, median |Δintercept|/range=0.941
- all: n_fit=4, median |Δslope|/|slope|=0.057, median |Δintercept|/range=1.511

## Per figure

| slug | split | correct | reason | n_gt | n_pred | worst NRMSE % | worst x-coverage | slope rel err | intercept / range | license | url |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| air-passengers-per-fatality | dev | no | series_count | 1 | 2 | 4.469 | 0.485 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/air-passengers-per-fatality |
| annual-fish-catch-taxa | held-out | no | series_count | 5 | 4 | 18.709 | 0.060 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-fish-catch-taxa |
| annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar | held-out | no | series_count | 1 | 2 | 0.224 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-number-of-people-receiving-antiretroviral-therapy-through-pepfar |
| annual-patents-invention-united-states-1790 | held-out | no | series_count | 1 | 3 | 0.219 | 0.535 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/annual-patents-invention-united-states-1790 |
| arable-land-pin | held-out | no | series_count | 1 | 2 | 0.221 | 0.080 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/arable-land-pin |
| arctic-sea-ice-coverage-19352014 | dev | no | series_count | 1 | 2 | 0.439 | 0.960 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/arctic-sea-ice-coverage-19352014 |
| aviation-fatalities-per-million-passengers | dev | no | series_count | 1 | 2 | 0.271 | 0.820 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/aviation-fatalities-per-million-passengers |
| banana-yields | dev | no | series_count | 3 | 4 | 2.700 | 0.040 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/banana-yields |
| bean-yields | dev | no | series_count | 4 | 5 | 21.256 | 0.045 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/bean-yields |
| biomass-fish-stocks-taxa | held-out | no | series_count | 1 | 2 | 0.745 | 0.040 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/biomass-fish-stocks-taxa |
| breast-cancer-death-rate-in-women | held-out | no | series_count | 6 | 5 | 11.747 | 0.070 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/breast-cancer-death-rate-in-women |
| cases-of-paralytic-polio-from-wild-polioviruses | held-out | no | no_calibration | 5 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cases-of-paralytic-polio-from-wild-polioviruses |
| cashew-nut-yields | held-out | no | nrmse_and_coverage | 4 | 4 | 40.246 | 0.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cashew-nut-yields |
| cholera-case-fatality-rate | held-out | no | series_count | 1 | 2 | 1.815 | 0.045 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cholera-case-fatality-rate |
| co2-long-term-concentration | held-out | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/co2-long-term-concentration |
| coal-output-per-worker-in-the-united-kingdom | held-out | no | series_count | 1 | 2 | 0.296 | 0.900 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/coal-output-per-worker-in-the-united-kingdom |
| cohort-fertility-rate | dev | no | x_coverage | 6 | 6 | 6.195 | 0.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cohort-fertility-rate |
| computer-chess-ability | dev | no | series_count | 1 | 2 | 0.121 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/computer-chess-ability |
| cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 | held-out | no | series_count | 1 | 2 | 0.232 | 0.855 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/cost-of-generating-electricity-new-capacity-using-photovoltaic-cells-in-the-us-19762009 |
| countries-with-a-signed-bilateral-investment-treaty | held-out | no | series_count | 2 | 3 | 0.256 | 0.860 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-a-signed-bilateral-investment-treaty |
| countries-with-an-inforce-bilateral-investment-treaty | held-out | no | series_count | 2 | 3 | 0.364 | 0.880 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/countries-with-an-inforce-bilateral-investment-treaty |
| crude-death-rate-hmd | dev | no | nrmse_and_coverage | 5 | 5 | 7.074 | 0.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/crude-death-rate-hmd |
| cumulative-space-visits | held-out | no | series_count | 4 | 5 | 0.824 | 0.010 | 0.007 | 0.050 | CC BY 4.0 | https://ourworldindata.org/grapher/cumulative-space-visits |
| daily-per-capita-caloric-supply | dev | no | series_count | 1 | 3 | 0.237 | 0.490 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/daily-per-capita-caloric-supply |
| deaths-and-disappearances-during-migration | held-out | no | series_count | 1 | 2 | 0.303 | 0.730 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-and-disappearances-during-migration |
| deaths-from-aids-un | dev | no | series_count | 1 | 2 | 1.416 | 0.910 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-aids-un |
| deaths-from-smallpox-in-london | dev | no | series_count | 1 | 3 | 6.607 | 0.070 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/deaths-from-smallpox-in-london |
| difference-in-female-and-male-life-expectancy-at-age-45 | held-out | no | x_coverage | 4 | 4 | 18.507 | 0.060 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/difference-in-female-and-male-life-expectancy-at-age-45 |
| different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk | dev | no | series_count | 2 | 3 | 0.102 | 0.635 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/different-ways-of-pushing-down-the-wage-setting-curve-the-netherlands-and-the-uk |
| diphtheria-cases-in-the-united-states | held-out | no | series_count | 1 | 2 | 3.285 | 0.830 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/diphtheria-cases-in-the-united-states |
| electric-car-stocks | dev | no | series_count | 4 | 5 | 0.574 | 0.025 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/electric-car-stocks |
| electricity-air-conditioning | dev | no | series_count | 1 | 2 | 0.074 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/electricity-air-conditioning |
| employment-in-the-coal-industry-in-the-united-kingdom | dev | no | series_count | 1 | 3 | 0.478 | 0.030 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/employment-in-the-coal-industry-in-the-united-kingdom |
| fatal-airliner-accidents-per-million-flights | held-out | no | series_count | 1 | 2 | 0.236 | 0.790 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fatal-airliner-accidents-per-million-flights |
| fatality-rates-due-to-lightning-in-the-us | dev | no | series_count | 1 | 2 | 0.605 | 0.970 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fatality-rates-due-to-lightning-in-the-us |
| fertilizer-total-use | dev | no | series_count | 1 | 2 | 0.160 | 0.945 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fertilizer-total-use |
| fish-catch-uk | held-out | no | series_count | 2 | 4 | 1.550 | 0.065 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fish-catch-uk |
| fish-discards | dev | no | series_count | 1 | 2 | 0.234 | 0.940 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/fish-discards |
| foreign-born-population-of-the-united-states | dev | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/foreign-born-population-of-the-united-states |
| global-commodity-prices-19602019 | held-out | no | series_count | 1 | 3 | 0.323 | 0.780 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-commodity-prices-19602019 |
| global-death-rate-in-violent-political-conflicts-over-the-long-run | held-out | no | series_count | 1 | 2 | 10.500 | 0.040 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-death-rate-in-violent-political-conflicts-over-the-long-run |
| global-deaths-in-violent-political-conflicts-over-the-long-run | dev | no | series_count | 1 | 3 | 11.639 | 0.030 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-deaths-in-violent-political-conflicts-over-the-long-run |
| global-plastics-production | dev | no | series_count | 1 | 2 | 0.115 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-plastics-production |
| global-smallpox-cases | held-out | no | series_count | 1 | 3 | 5.875 | 0.490 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/global-smallpox-cases |
| growth-of-global-trade | held-out | no | series_count | 1 | 3 | 0.183 | 0.690 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/growth-of-global-trade |
| heat-wave-index-usa | held-out | no | series_count | 1 | 3 | 5.032 | 0.110 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/heat-wave-index-usa |
| hepb3-number-unvaccinated | held-out | no | series_count | 1 | 2 | 0.534 | 0.045 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/hepb3-number-unvaccinated |
| homicide-rates-across-western-europe | dev | no | series_count | 5 | 6 | 17.284 | 0.010 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/homicide-rates-across-western-europe |
| incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 | dev | no | series_count | 1 | 2 | 0.096 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/incidence-of-hiv-the-share-of-new-infections-among-the-previously-uninfected-population-ages-15-49 |
| india-government-debt-as-a-percentage-of-gdp-19802019 | held-out | no | series_count | 1 | 2 | 1.025 | 0.775 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/india-government-debt-as-a-percentage-of-gdp-19802019 |
| indian-rhinos | held-out | no | series_count | 1 | 2 | 0.114 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/indian-rhinos |
| international-capital-flows | dev | no | series_count | 1 | 2 | 0.424 | 0.770 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/international-capital-flows |
| interpersonal-trust-in-the-us | dev | no | series_count | 1 | 2 | 0.180 | 0.815 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/interpersonal-trust-in-the-us |
| javan-rhinos | held-out | no | series_count | 1 | 2 | 0.123 | 0.715 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/javan-rhinos |
| labor-force-participation-rate-of-men-65-years-and-older-in-the-usa | held-out | no | series_count | 1 | 2 | 0.205 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-force-participation-rate-of-men-65-years-and-older-in-the-usa |
| labor-productivity-agriculture-sweden | dev | no | series_count | 1 | 2 | 0.278 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-agriculture-sweden |
| labor-productivity-per-hour | dev | no | series_count | 1 | 2 | 0.179 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/labor-productivity-per-hour |
| land-natural-share | held-out | no | x_coverage | 4 | 4 | 11.739 | 0.015 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/land-natural-share |
| land-use-agriculture-longterm | held-out | no | series_count | 1 | 2 | 0.080 | 0.970 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/land-use-agriculture-longterm |
| long-term-cod-catch | held-out | no | series_count | 1 | 2 | 0.770 | 0.870 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/long-term-cod-catch |
| macroplastics-in-ocean | dev | no | x_coverage | 3 | 3 | 1.939 | 0.255 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/macroplastics-in-ocean |
| maize-production | held-out | no | series_count | 5 | 4 | 28.547 | 0.075 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/maize-production |
| marriage-rate-per-1000-inhabitants | held-out | no | x_coverage | 5 | 5 | 10.916 | 0.085 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/marriage-rate-per-1000-inhabitants |
| material-footprint-per-capita | held-out | no | series_count | 1 | 2 | 0.062 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/material-footprint-per-capita |
| mention-of-the-word-capitalism-in-new-york-times-articles | held-out | no | series_count | 1 | 2 | 5.764 | 0.240 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/mention-of-the-word-capitalism-in-new-york-times-articles |
| microplastics-in-ocean | held-out | no | x_coverage | 3 | 3 | 5.172 | 0.165 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/microplastics-in-ocean |
| natural-resource-rents | dev | no | series_count | 1 | 2 | 0.380 | 0.810 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/natural-resource-rents |
| new-reported-cases-tetanus | held-out | no | series_count | 1 | 2 | 0.207 | 0.820 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/new-reported-cases-tetanus |
| nitrous-oxide-long | held-out | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/nitrous-oxide-long |
| northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c | dev | no | no_calibration | 1 | 0 | n/a | n/a | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/northern-hemisphere-temperatures-over-the-long-run-deviation-from-1951-1990-mean-temperature-c |
| northern-white-rhinos | held-out | no | series_count | 1 | 2 | 0.466 | 0.835 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/northern-white-rhinos |
| number-of-child-deaths-unwpp | held-out | no | series_count | 1 | 3 | 0.158 | 0.660 | 0.099 | 1.832 | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-child-deaths-unwpp |
| number-of-countries-having-implemented-a-vat | dev | no | series_count | 1 | 2 | 0.083 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-countries-having-implemented-a-vat |
| number-of-natural-disaster-events | held-out | no | series_count | 1 | 3 | 0.851 | 0.140 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-natural-disaster-events |
| number-of-patents-through-the-industrial-revolution | dev | no | series_count | 3 | 5 | 5.002 | 0.030 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-of-patents-through-the-industrial-revolution |
| number-un-peacekeeping-missions | held-out | no | series_count | 1 | 2 | 1.258 | 0.940 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/number-un-peacekeeping-missions |
| ozone-depleting-substance-emissions | dev | no | series_count | 2 | 3 | 0.147 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substance-emissions |
| ozone-depleting-substances-index | held-out | no | series_count | 1 | 2 | 0.169 | 0.680 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/ozone-depleting-substances-index |
| palm-oil-production | dev | no | series_count | 1 | 3 | 0.173 | 0.620 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/palm-oil-production |
| percentage-of-persons-without-health-insurance-coverage-us | held-out | no | series_count | 1 | 2 | 0.132 | 0.845 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/percentage-of-persons-without-health-insurance-coverage-us |
| population-growth-rate | held-out | no | series_count | 1 | 2 | 0.895 | 0.515 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/population-growth-rate |
| population-of-england-millennium | dev | no | series_count | 1 | 2 | 0.129 | 0.995 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/population-of-england-millennium |
| population-unwpp | dev | no | x_coverage | 3 | 3 | 61.557 | 0.005 | 3.747 | 13.499 | CC BY 4.0 | https://ourworldindata.org/grapher/population-unwpp |
| prevalence-of-undernourishment-in-developing-countries-since-1970 | held-out | no | x_coverage | 1 | 1 | 0.173 | 0.050 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/prevalence-of-undernourishment-in-developing-countries-since-1970 |
| public-trust-in-government | dev | no | series_count | 1 | 2 | 0.611 | 0.880 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/public-trust-in-government |
| reported-share-of-people-experiencing-homelessness | dev | no | series_count | 1 | 2 | 0.079 | 0.885 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/reported-share-of-people-experiencing-homelessness |
| rubella-cases-in-the-united-states | held-out | no | series_count | 1 | 3 | 0.161 | 0.680 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/rubella-cases-in-the-united-states |
| same-sex-marriage-country-count | held-out | no | series_count | 1 | 2 | 1.153 | 0.530 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/same-sex-marriage-country-count |
| share-of-agriculture-in-total-employment | held-out | no | series_count | 1 | 2 | 0.107 | 0.855 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-agriculture-in-total-employment |
| share-of-the-workforce-employed-in-the-coal-industry-united-kingdom | dev | no | series_count | 1 | 2 | 0.641 | 0.975 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/share-of-the-workforce-employed-in-the-coal-industry-united-kingdom |
| southern-white-rhinos | held-out | no | series_count | 1 | 3 | 0.075 | 0.745 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/southern-white-rhinos |
| stomach-cancer-death-rate | dev | no | series_count | 6 | 4 | 9.165 | 0.040 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stomach-cancer-death-rate |
| stratospheric-chorine-concentrations | dev | no | x_coverage | 3 | 3 | 22.858 | 0.015 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-chorine-concentrations |
| stratospheric-ozone-concentration-projections | dev | no | x_coverage | 3 | 3 | 5.750 | 0.130 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/stratospheric-ozone-concentration-projections |
| supercomputer-power-flops | dev | no | series_count | 1 | 3 | 0.799 | 0.780 | 0.015 | 1.189 | CC BY 4.0 | https://ourworldindata.org/grapher/supercomputer-power-flops |
| the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 | dev | no | series_count | 1 | 2 | 0.926 | 0.915 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-amount-of-cod-caught-in-the-grand-banks-north-atlantic-fisheries-18512018 |
| the-growth-of-government-in-the-uk | dev | no | series_count | 1 | 2 | 0.578 | 0.895 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-growth-of-government-in-the-uk |
| the-number-of-reported-paralytic-polio-cases | held-out | no | series_count | 1 | 2 | 0.279 | 0.935 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/the-number-of-reported-paralytic-polio-cases |
| total-agricultural-land-use-per-person | dev | no | series_count | 1 | 2 | 0.140 | 0.990 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/total-agricultural-land-use-per-person |
| tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv | held-out | no | series_count | 1 | 3 | 0.095 | 0.025 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/tuberculosis-mortality-rates-excludes-people-who-are-also-infected-with-hiv |
| uk-gdp-growth-19572016 | held-out | no | series_count | 1 | 2 | 7.174 | 0.470 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-gdp-growth-19572016 |
| uk-government-debt-as-a-percentage-of-gdp-17272016 | held-out | no | series_count | 1 | 2 | 0.974 | 0.880 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-government-debt-as-a-percentage-of-gdp-17272016 |
| uk-inflation-rate-19892019 | held-out | no | series_count | 1 | 2 | 0.238 | 0.965 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-inflation-rate-19892019 |
| uk-unemployment-rate-19712017 | dev | no | series_count | 1 | 2 | 0.486 | 0.985 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/uk-unemployment-rate-19712017 |
| un-projection-of-annual-infant-deaths | dev | no | x_coverage | 1 | 1 | 0.079 | 0.770 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/un-projection-of-annual-infant-deaths |
| wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 | held-out | no | series_count | 1 | 2 | 2.686 | 0.680 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wage-of-craftsmen-relative-to-that-of-laborers-in-england-1200-2000 |
| wages-relative-to-the-cost-of-capital | held-out | no | series_count | 2 | 3 | 0.294 | 0.030 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wages-relative-to-the-cost-of-capital |
| what-percentage-of-the-us-public-approves-of-working-wives | held-out | no | series_count | 1 | 2 | 0.171 | 1.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/what-percentage-of-the-us-public-approves-of-working-wives |
| wildlife-exports | held-out | no | series_count | 6 | 5 | 20.477 | 0.000 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/wildlife-exports |
| working-hours-uk-millennium | dev | no | series_count | 1 | 2 | 3.753 | 0.730 | n/a | n/a | CC BY 4.0 | https://ourworldindata.org/grapher/working-hours-uk-millennium |
