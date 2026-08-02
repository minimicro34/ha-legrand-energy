# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

---

## 1.0.5 - 2026-08-03

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
