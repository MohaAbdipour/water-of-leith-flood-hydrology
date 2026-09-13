# Methodology rationale

Short notes on why specific analytical choices were made in this study,
gathered in one place for reference alongside the fuller descriptions in
`README.md`.

## Three flood-frequency distributions, not one

GEV, Gumbel and Log-Pearson III were fitted rather than committing to a
single model up front. The three make different tail assumptions, and the
31-year record is too short to select decisively between them on fit alone
(all ΔAICc values are below 2). Reporting all three, and their divergence at
Q100, is the point of the study rather than a limitation to be hidden behind
one number.

## AICc rather than plain AIC

The small-sample correction term `2k(k+1)/(n-k-1)` matters at n = 31 with
k = 2–3 parameters; plain AIC would understate the penalty for the extra
parameter in GEV and Log-Pearson III relative to Gumbel.

## Gringorten plotting positions for empirical return periods

Gringorten plotting positions provide a conventional empirical probability
scale for displaying ordered annual maxima against the fitted curves. They are
used only for the probability plot and not for parameter estimation, which is
by maximum likelihood. No claim of universal unbiasedness is made.

## Non-parametric bootstrap rather than the delta method

Each bootstrap resample is refit from scratch (not just resampled around a
fixed parameter estimate), so the reported intervals include both sampling
and re-estimation uncertainty. This avoids relying on asymptotic normality
assumptions that are weak at n = 31.

## POT threshold and 72-hour declustering

The 99.7th-percentile threshold was chosen to land close to the conventional
"POT3" density (~3 independent events/year) while remaining a transparent,
reproducible rule rather than a curated selection. The 72-hour run-length was
tested against alternatives from 24 hours to 7 days (`pot_independence_sensitivity.csv`)
to confirm the main POT conclusions do not hinge on that one choice.

## Poisson–GPD return levels, not a 1/T approximation

Return levels use the exact Poisson relationship between the exceedance rate
and the annual non-exceedance probability (`-log(1 - 1/T)`) rather than
approximating the threshold-crossing rate as `1/T`. The numerical difference
is greatest at short return periods and becomes small as `T` increases.

## Fixed bootstrap seed (19006, the station number)

Every stochastic routine seeds `numpy.random.default_rng` with the station
number so that reruns are byte-for-byte reproducible — confirmed directly by
diffing regenerated outputs against the committed ones.

## Rank-based Ljung–Box for POT event independence

Autocorrelation was computed on ranked, not raw, peak magnitudes so that one
or two exceptional floods don't dominate the statistic in a 79–99 event
sample. This is explicitly reported as a supporting diagnostic, not proof of
meteorological independence or compliance with a formal event-separation
procedure.

## Circular statistics for flood seasonality

Water-year timing wraps at the 30 September / 1 October boundary, so a
calendar histogram or arithmetic mean would incorrectly split events that
cluster around that boundary. Treating timing as an angle (mean resultant
vector, Rayleigh test) keeps events near the wrap point together.

## Chronological, expanding-window validation for the wetness model

Each test point is predicted using only model coefficients fit on
chronologically earlier events, which is the leakage-safe way to ask whether
antecedent-rainfall and seasonal terms have real predictive value rather than
just describing the sample they were fit on. This is why the negative
result (no out-of-time improvement over the baseline) is reported instead of
a same-sample R².

## Partial Spearman, not partial Pearson, for controlling variables

Rainfall–flow associations are monotonic but not demonstrably linear, so
correlations are computed on ranks; the "partial" step residualises ranked
predictor and outcome on the ranked control variable by OLS before
correlating the residuals, which avoids assuming a linear relationship on the
raw values.

## Terrain-derived catchment boundary kept independent of the NRFA polygon

Two separate reasons, not one: the NRFA catchment boundary is licence-restricted
and cannot be redistributed, so an open, reproducible study needs its own
delineation; and keeping the two independent is what makes the area
comparison (112.56 km² vs. the published 107 km²) a genuine cross-check
rather than a circular one.

## Open-record and full-NRFA-record results kept separate, not merged

Combining the 31-year open UK-Flow15 overlap with the 62-year restricted
NRFA record would obscure the very record-length effect on Q100 that the
sensitivity analysis is designed to show, and would mix data released under
different licence terms.

## Design-flow language deliberately avoided

The station's NRFA classification is "suitable for pooling," not "suitable
for QMED," and 31–62 years is a short base for extrapolating to 100–200-year
return periods. Results are reported as diagnostics throughout rather than
as approved design flows, consistent with the "Scientific limitations"
section of `README.md`.
