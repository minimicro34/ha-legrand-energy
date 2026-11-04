# Netatmo historical energy chart experiment

Status: experimental; no production behavior changed.

## Observations (2026-11-04)

- `MeasurementService` already requests current-day measurements from midnight using `scale="5min"`, and prior dates using `scale="1day"`.
- The decoder returns per-module `EnergyPoint(timestamp, energy, price, interval_seconds, tariff, zone_id)`; `energy` is in Wh, converted to kWh by `MeasurementProcessor`.
- A diagnostic of live API responses showed 31 points per reporting module, starting at `2026-11-03T23:02:30Z` and ending at `2026-11-04T13:27:30Z`, with `interval_seconds=1500` despite a requested `5min` scale. This is not evidence of 5-minute resolution. Some modules returned no points.
- The Lovelace chart currently reads Home Assistant Recorder statistics rather than these private API points.
- Current-day retry backoff (2, 5, 10, 15 minutes) applies to API exceptions, not to a successful response with no measurements. Empty successful responses reset the error backoff.

## Required validation before switching the chart source

1. Identify the total-electricity module, rather than summing overlapping module totals.
2. Confirm that the API's point timestamp denotes interval start, and inspect whether returned points are contiguous or aggregated.
3. Verify energy sums against Home + Control for a day when Home Assistant was offline; compare units and local timezone/DST boundaries.
4. Expose data to Lovelace through a bounded, authenticated Home Assistant interface; do not publish private API tokens or raw response payloads.
5. Define source precedence and avoid mixing Recorder and API intervals twice. Preserve a clear unavailable/partial-data state.
6. Add tests for missing intervals, irregular `step_time`, empty modules, Wh-to-kWh conversion, and local midnight/DST.
7. Test empty current-day responses and recovery separately from API-error backoff; avoid extra polling under future rate limits.

## Local testing

Do **not** install this branch on Home Assistant until the history endpoint, frontend changes, and regression tests are committed and CI passes. The current branch only contains this investigation document.
