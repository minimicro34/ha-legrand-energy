# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

---

## [1.3.3] - Unreleased

### Added
- Restored native Home + Control cached interval history for Day, Week, Month, and Year charts, with native HP/HC measurements and authenticated WebSocket access.
- Added a read-only `legrand_energy.debug_tariff_fields` action for investigating private Netatmo tariff and daily electricity fields.
- Added source timestamps, measurement age, and freshness information for interval-average power sensors.
- Added estimated electricity costs to chart tooltips using current HP/HC contract rates (not historical billed prices).
- Added an estimated average power for the unmonitored **Reste de la maison** circuit, calculated from the whole-house and measured-circuit average powers only when readings are available and synchronized.

### Changed
- Updated the bundled Lovelace card to **1.0.4** with native-history charts, clearer fallback information, power freshness indicators, and interactive HP/HC tooltips.
- Retained recent valid average-power measurements for up to 60 minutes during temporary private API failures, without extending their source timestamps.
- Restricted detailed current-day API measurement diagnostics to DEBUG logging.
- Limited push-triggered GitHub Actions checks to `main` to avoid duplicate runs alongside pull-request checks.
- Refresh the cached private `/homesdata` response every 15 minutes with `sync_measurements=true` to investigate whether EcoMeter measurements synchronize without opening Home + Control, while preserving existing five-minute measurement polling.

### Fixed
- Recovered native cached history promptly after a temporary Home Assistant Recorder fallback.
- Stabilized the Day chart after midnight: previous-day consumption is not displayed as current-day consumption while awaiting the first new measurements.
- Restored HP tooltip interaction on stacked chart overlays and corrected singular wording for one chart period.
- Improved handling of stale, invalid, future-dated, or incomplete average-power measurements.

### Validation
- Expanded Python and JavaScript regression coverage for native history, tariff diagnostics, cached power, fallback recovery, and card interactions.
- CI, Hassfest, and HACS Validation passed for the remainder-power pull request (#16).
- Home Assistant testing confirmed automatic arrival of the first post-midnight readings and matching HP/HC energy and estimated costs against Home + Control.
- Six Lovelace card screenshots (Day, Week, Month, Year, Circuits, Diagnostics) are planned for `docs/` before the stable release.

### Beta 13 — Periodic Home + Control measurement synchronization

#### Changed
- Refresh the cached private `/homesdata` response every 15 minutes with `sync_measurements=true` instead of retaining it indefinitely, to investigate whether EcoMeter readings synchronize without opening Home + Control.
- Preserve existing five-minute `gethomemeasure` polling, entity identifiers, and energy calculations.

#### Tests
- Add regression coverage for cache reuse before expiry, periodic refresh after 15 minutes, and explicit `force_refresh=True` behavior.
- Confirm local `make check` passes with 197 Python tests, 27 JavaScript tests, and 91.16% Python coverage.

### Beta 12 — Midnight display stabilization

#### Added
- Added estimated euro costs to chart tooltips using the configured HP/HC contract rates, without treating current prices as historical billed prices.

#### Improved
- Updated the bundled Lovelace card to version `1.0.4`.
- Enabled HP segment tooltips on hover and click, matching the existing HC behavior.

#### Fixed
- Stabilized the Day chart's empty state before the first current-day measurements become available.
- Corrected singular wording for a single chart period.
- Restored HP tooltip interaction on the stacked chart overlay without adding duplicate keyboard-focusable bars.

#### Tests
- Added JavaScript regression assertions for HP overlay interactions.
- Expanded coordinator regression coverage for tariff, Home + Control, and native price diagnostics.

### Beta 11 — Daily native HP/HC diagnostics

#### Added
- Logged native daily electricity and price totals to help investigate HP/HC mapping in the private Netatmo response.

#### Changed
- Kept diagnostic output separate from energy and tariff attribution used by sensors and charts.

### Beta 10 — Native Netatmo tariff diagnostics

#### Added
- Extended `legrand_energy.debug_tariff_fields` to inspect raw private `gethomemeasure` electricity and price fields (`sum_energy_elec`, `sum_energy_elec$0/$1/$2`, and `sum_energy_price$0/$1/$2`).
- Logged per-day availability, timestamps, and representative first and last non-null price rows.

#### Improved
- Used UTC-aware timestamps and cleaned up the read-only diagnostic output.

#### Changed
- Kept native HP/HC price mapping unassigned until verified against actual API responses; no change to sensor energy, cost calculations, or tariff attribution.

#### Validation
- Local validation reported 184 Python tests, 27 JavaScript tests, 86.62% coverage, and `make check` passing.

### Beta 9 — Tariff and midnight diagnostics

#### Added
- Registered the `legrand_energy.debug_tariff_fields` Home Assistant action.
- Added INFO-level tariff-field and midnight diagnostic reporting for investigating the private API response.

#### Changed
- Kept diagnostic collection read-only.

### Beta 8 — Recorder fallback recovery

#### Fixed
- Retried cached Netatmo history promptly after Recorder fallback rather than waiting indefinitely.
- Avoided scheduling a recovery retry when the integration entry was unknown.
- Displayed the Recorder recovery notice only when native history was eligible.

#### Improved
- Made the fallback source more explicit in the Lovelace card.

#### Validation
- Added JavaScript regression coverage for timed fallback recovery and card version 1.0.3.

### Beta 7 — Current-day measurement diagnostics

#### Added
- Added safe current-day API and decoder count diagnostics to investigate delayed native measurements.

#### Changed
- Restricted detailed current-day API counts to DEBUG logging.
- Simplified diagnostic metadata without exposing private measurements or credentials.

### Beta 6 — Native history restoration

#### Added
- Restored Netatmo / Home + Control cached interval history as the preferred source for Day, Week, Month, and Year charts.
- Restored authenticated cached-history WebSocket access, interval serialization, and native HP/HC measurements.

#### Improved
- Kept Home Assistant Recorder as fallback when the integration cache is unavailable or empty, and retried native history after startup.
- Updated the bundled Lovelace card to version 1.0.2.

#### Validation
- Python and JavaScript regression tests cover native history.
- CI, HACS Validation, and Hassfest passed on the beta6 pull request.

### Beta 5 — Average-power freshness and resilience

#### Added
- Exposed source timestamps, measurement age, and freshness attributes for average-power sensors.
- Displayed average-power freshness in the Lovelace card and introduced an independent card version (1.0.1).
- Added regression tests for cached averages, expiry boundaries, and invalid timestamps.

#### Changed
- Retained the last valid average-power reading for up to 60 minutes without extending its source timestamp.
- Restricted GitHub Actions push triggers to `main` to avoid duplicate runs alongside pull-request checks.

#### Improved
- Preserved recent cached average power during temporary API failures and missing measurement intervals.
- Improved validation of stale, future-dated, and incomplete cached readings.

#### Fixed
- Prevented total and circuit average-power sensors from becoming unavailable while recent valid readings still exist.

#### Validation
- At the beta5 changelog update: 90.14% Python coverage and 21 JavaScript tests passed; Ruff, Mypy, CI, HACS Validation, and Hassfest had passed before the final card-version and changelog edits.

### Beta 4 — Native interval processing

#### Changed
- Updated native measurement history and private measurement decoding used by the integration and card.
- Updated the energy-series processing and current-day history handling.

#### Validation
- Added or updated regression tests for the private measurement decoder, measurement history, and Lovelace card.

### Beta 3 — Measurement-history reliability

#### Fixed
- Adjusted coordinator and measurement-history handling for native interval updates.

#### Validation
- Updated measurement-history regression tests.

### Beta 2 — Lovelace card refinement

#### Changed
- Refined the bundled Lovelace card's display behavior.

#### Validation
- Updated Lovelace card regression tests.

### Beta 1 — Native history groundwork

#### Added
- Introduced integration-side native measurement history support, WebSocket handling, and diagnostics for the 1.3.3 beta series.
- Added regression coverage for measurement history, WebSocket, diagnostics, and Lovelace chart behavior.

#### Changed
- Updated the coordinator, measurement service, and Lovelace card to support native-history experimentation.

---

[1.3.3]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.3.2...v1.3.3

---

## [1.3.2] - 2026-11-04

### Changed

- Clarified the Day chart footer when Legrand's daily total exceeds the energy covered by Recorder statistics.
- Distinguished unavailable or non-comparable Recorder history from N/R energy, which remains reserved for measured deltas spanning missing five-minute samples.
- Kept chart energy calculations and existing entity identifiers unchanged.

### Validation

- Added a JavaScript regression test for an uncovered Recorder history gap.
- GitHub Actions CI, Hassfest, and HACS Validation passed for PR #13.

---

[1.3.2]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.3.1...v1.3.2

---

## [1.3.1] - 2026-11-04

### Added

- Regression tests for Week and Month chart calendar axes.
- Automated regression test ensuring English translations remain synchronized with `strings.json`.
- Regression tests for initial device registration, missing parent lookup, and authentication session lifecycle.

### Fixed

- Week chart now displays all seven calendar days, including days without Recorder statistics.
- Month chart now displays all 28, 29, 30, or 31 calendar days.
- Improved Month chart date label spacing while preserving the final calendar day's label.
- Missing Recorder measurements are no longer represented as zero consumption.
- Restored English translations for `average_power` and `circuit_average_power` sensors.
- Fixed EcoMeter device registration during initial setup, preventing missing-parent errors on first installation.
- Fixed circuit parent device lookup when the parent is not yet registered, preserving existing entity identifiers and Recorder history.
- Fixed Home Assistant-managed aiohttp sessions being closed during private authentication and reconfiguration.

### Validation

- 147 Python tests passed.
- 20 JavaScript tests passed.
- 90.47% Python coverage.
- `make check` and GitHub Actions CI passed.

Thanks to @frenck for reporting the English translation issue.

---

[1.3.1]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.3.0...v1.3.1

---

## [1.3.0] - 2026-10-25

Cumulative changes since 1.2.0, including the full beta development and final stabilization.

### Added

- Bundled **Legrand Energy Lovelace card**, with an energy/power/cost/tariff summary, Day/Week/Month/Year charts, contract information, and expandable Circuits and Diagnostics panels.
- Automatic JavaScript resource serving and registration for storage-managed Home Assistant dashboards, without a separate HACS card repository.
- Automatic EcoMeter and circuit entity discovery through Home Assistant's entity registry, including renamed sensors and multiple EcoMeters.
- Real Recorder-based **HP/HC** consumption breakdown and stacked chart bars, rather than estimating energy from tariff change times alone.
- Five-minute Recorder aggregation into **30-minute Day bars**, with hourly fallback when fine-grained statistics are unavailable.
- Explicit gray **N/R** bar and missing-interval information for energy that cannot safely be attributed to a half-hour.
- Average-power entities for the main EcoMeter and individual electrical circuits, calculated from measured energy and interval duration rather than presented as instantaneous power.
- Sanitized Home + Control status diagnostic service for troubleshooting without logging private credentials.
- JavaScript Lovelace regression tests and broader Python tests integrated into `make check` and GitHub Actions CI.

### Changed

- Improved chart layout, time and kWh axes, interactive tooltips, responsive card grid sizing, and preservation of expanded sections across state updates.
- Improved Day charts for 24/25-hour daylight-saving days, including distinct labels for both occurrences of 02:00 during the autumn clock change.
- Displayed the current tariff and next change more clearly, with contract energy prices shown to four decimal places.
- Added first-hour live energy fallback when Recorder has not yet populated the first chart bucket.
- Kept all twelve months visible in Year view, leaving months with unavailable statistics blank rather than displaying false zero consumption.
- Aligned Recorder monthly cumulative deltas and HP/HC splits with their calendar months, and calculated the ongoing partial month separately from daily statistics.
- Refined circuit labels and circuit energy/cost breakdown, without mixing devices belonging to different EcoMeters.
- Preserved historical energy totals while avoiding stale average-power readings after failed private measurement updates.
- Preserved measurement interval metadata and improved midnight/current-day consumption handling.

### Fixed

- Corrected Recorder timestamps reported in seconds or milliseconds, and included the preceding statistics bucket so the first visible delta is not lost.
- Prevented consumption spanning missing five-minute samples from being assigned to a fictitious time slot or counted twice across overlapping history loads.
- Improved fallback handling when Recorder has no fine-grained data, and synchronized HP/HC aggregation with the selected statistics period.
- Corrected monthly HP/HC alignment, missing-current-month behavior, and duplicated or shifted values in Year view.
- Improved private authentication cookie isolation by using dedicated HTTP sessions for private sign-in and API requests.
- Redacted credentials, tokens, cookie values, and location coordinates from diagnostics and removed sensitive token fragments from logs.

### Internal

- Added automated coverage for Home Assistant setup, OAuth/private authentication, entity discovery, power conversion, Recorder charts, missing samples, DST, monthly boundaries, and diagnostics privacy.
- Enforced at least 80% Python test coverage and expanded CI, Hassfest, and HACS validation checks.
- Removed temporary private-measurement and historical-availability debug probes used during beta investigation; they are **not** part of the shipped integration.

### Final stabilization fixes

- Recover the first recorded month of the year chart from daily Recorder cumulative statistics when its monthly predecessor is unavailable and a complete daily baseline exists, without shifting later months or inventing missing readings. Leave the month blank when the first-day baseline or completed-month evidence is missing. Recover HP/HC values when their daily statistics are available.
- Subtract separately displayed, unallocated N/R energy from the Day chart's **remaining difference**, avoiding a misleading discrepancy when Recorder has missing five-minute samples.
- Visually separate the non-temporal **N/R** bar and its axis label from the final time-of-day bar.
- Display a first month with mid-month Recorder history as an explicitly marked **partial** gray bar, showing its first recorded date in the tooltip instead of claiming a full-month total.

### Final validation and documentation

- Add regression tests for first-month reconstruction, preservation of subsequent monthly HP/HC values, N/R spacing, and day-total reconciliation.
- Clarify automatic Lovelace resource registration, optional manual setup, Recorder history limitations, and N/R behavior.
- Add six README screenshots: **Day, Week, Month, Year, Circuits, Diagnostics**, stored under `docs/`.

### Notes

- The Lovelace card reads Home Assistant Recorder statistics and does not import old Home + Control measurements into Recorder.
- A blank month means the available statistics do not justify a consumption value; a gray partial-month bar includes only recorded consumption and does not estimate missing days. An unallocated N/R amount cannot safely be assigned to a specific time slot.
- Final Home Assistant validation confirmed: Day, Week, Month, and Year energy totals match the Legrand website. The Year chart begins in July because earlier Home Assistant Recorder history is unavailable, while the annual total remains consistent with Legrand.


---

[1.3.0]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.2.0...v1.3.0

---

## [1.2.0] - 2026-08-29

### Added

- Added native Home Assistant reconfiguration for Netatmo / Home + Control email and password.
- Added OAuth2 reauthentication when the Netatmo authorization becomes invalid.
- Added automated tests covering configuration, reconfiguration, and OAuth2 reauthentication flows.

### Changed

- Replaced the private authentication Options Flow with Home Assistant's native config entry reconfiguration flow.
- Private Home + Control authentication data is now stored and updated directly in the config entry.
- Reconfiguration now validates the new Home + Control credentials before updating and reloading the integration.
- OAuth2 reauthentication updates the existing config entry while preserving private Home + Control authentication data.
- Updated authentication documentation to distinguish OAuth2 Application Credentials from Home + Control account credentials.

### Fixed

- Prevented duplicate config entry reloads caused by combining an update listener with config flow reload methods.
- Improved compatibility with Home Assistant 2026.12, where the previous double-reload pattern is no longer supported.

### Internal

- Removed the legacy `LegrandEnergyOptionsFlow`.
- Removed the manual config entry update listener used by the previous Options Flow.
- Added unit and Home Assistant framework tests for the authentication flows.

[1.2.0]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.1.0...v1.2.0

---

## [1.1.0] - 2026-08-04

### Added

- Added automatic detection of water and gas modules.
- Added support for cold water, hot water, and gas measurements.
- Added daily, weekly, monthly, and yearly fluid consumption entities.
- Added water and gas cost entities when price data is available from Home + Control.
- Added generic fluid measurement types, models, processing helpers, and private API measurement handling.
- Added a generic decoder for electricity, water, and gas responses.
- Added reusable retry backoff helper shared by historical and current-day private measurement updates.
- Added progressive retry backoff for current-day private measurements (2, 5, 10 and 15 minutes).
- Added automatic retry backoff for historical private measurements.
- Added recovery logs when private measurements become available again.
- Added English and French translations for water and gas entities.
- Added automated tests for fluid type detection, decoding, processing, retry backoff, and data access.

### Changed

- Generalized private measurement requests to support electricity, water, and gas.
- Extended the measurement service and coordinator to store fluid measurements separately from electricity.
- Updated module discovery to classify electricity, water, and gas circuits.
- Updated the sensor platform to expose entities according to each module's fluid type.
- Cached historical private measurements continue to be refreshed only when needed.
- Cached measurements remain available while waiting for the private API to recover.
- Reduced repeated calls to the Home + Control private API during temporary outages.
- Gas values reported by Home + Control in dm³ are exposed as litres for Home Assistant compatibility.

### Fixed

- Prevented repeated private API requests every polling cycle during prolonged timeouts or connection failures.
- Improved resilience when Home + Control private measurements temporarily return timeouts, connection resets, or backend errors.
- Improve OAuth2 setup robustness.
- Automatically retry setup when Netatmo OAuth servers are temporarily unavailable.
- Trigger Home Assistant reauthentication when OAuth refresh fails with an authentication error.

### Internal

- Preserved the existing electricity measurement and tariff pipelines.
- Added reusable fluid measurement architecture for future supported resources.
- Refactored the private measurement decoder for improved readability and maintainability.

[1.1.0]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.0.6...v1.1.0

---

## [1.0.6] - 2026-08-04

### Changed

- Cached historical (`scale=1day`) private measurements in memory.
- Historical measurements are refreshed only at startup and after a calendar day change.
- Current-day (`scale=5min`) measurements continue to refresh every coordinator update.
- Refactored the private measurement decoder for improved readability and maintainability.

### Improved

- Significantly reduced calls to the Home + Control private measurement endpoints.
- Reduced the risk of HTTP 500/502 errors caused by repeated historical requests.
- Expanded unit test coverage for measurement caching and private response decoding.

---

## [1.0.5] - 2026-08-03

### Fixed

- Fixed parsing of `gethomemeasure` responses using the compact `sum_energy_elec` format.
- Added automatic fallback between total energy (`sum_energy_elec`) and tariff-specific values (`sum_energy_elec$0/$1/$2`).
- Improved compatibility with different Legrand Energy API response formats.

---

## [1.0.4] - 2026-08-02

### Changed

- Improved Netatmo private authentication refresh reliability.
- Improved handling of expired private authentication sessions.
- Better recovery after temporary HTTP 401/403 responses.
- Better handling of Netatmo API rate limits.
- Improved resilience by keeping cached data during temporary private API failures.
- Improved debug logging for authentication troubleshooting.
- Internal code cleanup and refactoring.

### Fixed

- Prevent unnecessary configuration failures caused by temporary private authentication errors.
- Various stability improvements.

---

## [1.0.3] - 2026-08-01

### Added

- Daily, monthly and yearly energy and cost projections.

### Changed

- Automatic cleanup of legacy entity identifiers.

### Fixed

- Removed the redundant peak-hours binary sensor that appeared as an unnamed entity.
- Preserved the useful off-peak-hours binary sensor.

---

## [1.0.2]

### Added

- Electricity contract information.
- Current tariff detection.
- Current electricity price.
- Next tariff change.
- Daily, weekly, monthly and yearly energy consumption.
- Daily, weekly, monthly and yearly cost calculation.
- Energy Dashboard compatibility.

### Changed

- Improved circuit discovery.
- Improved diagnostics support.

---

## [1.0.1]

### Added

- Initial public release.
- OAuth2 authentication.
- Automatic EcoMeter discovery.
- Automatic circuit discovery.
- Automatic OAuth token refresh.
- Automatic private Netatmo session management.
