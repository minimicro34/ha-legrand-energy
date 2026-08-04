# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

---

## [1.1.0] - 2026-08-04

### Added

- Added water and gas module detection.
- Added support for cold water, hot water, and gas measurements.
- Added daily, weekly, monthly, and yearly fluid consumption entities.
- Added water and gas cost entities when price data is available from Home + Control.
- Added generic fluid measurement types and private API measurement handling.
- Added a generic decoder for electricity, water, and gas responses.
- Added dedicated fluid measurement models and processing helpers.
- Added English and French translations for water and gas entities.
- Added automated tests for fluid type detection, decoding, processing, and data access.

### Changed

- Generalized private measurement requests to support electricity, water, and gas.
- Extended the measurement service and coordinator to store fluid measurements separately from electricity.
- Updated module discovery to classify electricity, water, and gas circuits.
- Updated the sensor platform to expose entities according to each module's fluid type.
- Gas values reported by Home + Control in dm³ are exposed as litres for Home Assistant compatibility.

### Internal

- Preserved the existing electricity measurement and tariff pipelines.
- Added reusable fluid measurement architecture for future supported resources.

[1.1.0]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.0.6...v1.1.0

---

## [1.0.7] - 2026-08-04

### Added

- Added progressive retry backoff for current-day private measurements.
- Added retry backoff support for historical private measurements.
- Added recovery logs when private measurements become available again.
- Added automated tests for retry timing, reset behavior, and recovery handling.

### Changed

- Reduced repeated calls to the private Home + Control API during temporary outages.
- Current-day measurement retries now progressively wait 2, 5, 10, then 15 minutes after consecutive failures.
- Historical measurement retries remain delayed by 15 minutes after a failure.
- Cached measurements continue to be exposed while waiting for the private API to recover.

### Fixed

- Prevented repeated private API requests every polling cycle during prolonged timeouts or connection failures.
- Improved stability when `gethomemeasure` temporarily returns timeouts, connection resets, or backend errors.

[1.0.7]: https://github.com/minimicro34/ha-legrand-energy/compare/v1.0.6...v1.1.0

---

## [1.0.6] - 2026-08-04

### Changed

- Cached historical (`scale=1day`) private measurements in memory.
- Historical measurements are now refreshed only:
  - at startup,
  - after a day change,
  - after a 15-minute retry delay following a temporary failure.
- Current-day (`scale=5min`) measurements continue to refresh every coordinator update.
- Refactored the private measurement decoder for improved readability and maintainability.

### Improved

- Significantly reduced calls to the Netatmo private `gethomemeasure` endpoint.
- Reduced the risk of HTTP 500/502 errors caused by repeated historical requests.
- Historical measurements are preserved during temporary private API failures.
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

---

## [1.0.0]

🎉 First stable release

Initial stable release of the Legrand Energy integration for Home Assistant.

- Features
- OAuth2 authentication
- Private API support
- Electricity contract parsing
- Peak / Off-Peak tariff detection
- Current tariff and next change sensors
- Daily, monthly and yearly consumption
- Cost calculation
- Consumption projections
- Diagnostics support
- HACS compatible
- Quality
- Full type checking with mypy
- Ruff formatted
- Automated tests
- Home Assistant best practices
