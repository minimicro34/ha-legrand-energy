# Legrand Energy for Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![CI](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml/badge.svg)](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE)
[![Hassfest](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/hassfest.yml/badge.svg)](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/hassfest.yml)

A Home Assistant custom integration for **Legrand EcoMeter** installations using **Home + Control / Netatmo** services.

The integration automatically discovers your EcoMeter installation and electrical circuits, retrieves energy measurements, calculates electricity costs according to your tariff, and exposes contract information directly in Home Assistant.

> ⚠️ This integration relies on both public and undocumented Netatmo APIs. Some advanced features may stop working if Netatmo changes its web services.

---

## Features

### Energy monitoring

- ⚡ Automatic EcoMeter and circuit discovery
- 📊 Daily, weekly, monthly and yearly energy consumption
- 💶 Energy cost calculation
- 📈 Energy and cost projections
- 🔌 Per-circuit energy and cost monitoring

### Tariffs & contract

- 📋 Electricity contract information
- 🟢 Peak / Off-peak tariff detection
- 💲 Current electricity price
- ⏰ Next tariff change

### Home Assistant

- 🏠 Energy Dashboard compatible
- 🔄 Config Flow
- 🔐 OAuth2 authentication
- ⚙️ Options Flow
- 🩺 Diagnostics support
- 📦 HACS compatible

### Reliability

- 🔄 Automatic OAuth token refresh
- 🔐 Automatic private session renewal
- 🛡️ Automatic recovery from temporary API errors
- 📉 Graceful handling of Netatmo API rate limits
- 🚀 Intelligent caching of historical measurements to reduce private API traffic

## Known limitations

- Week, month, and year totals use the historical measurements available from Home + Control for the current calendar year.
- Historical totals before January 1 of the current year are not exposed as entities.
- Some advanced features rely on undocumented Netatmo web services and may be affected by future changes made by Netatmo.
- Changes to Netatmo private APIs may temporarily affect contract or tariff information.

---

## Supported devices

Currently tested with:

- ✅ Legrand EcoMeter
- ✅ Home + Control / Netatmo energy installations
- ✅ Electrical circuits discovered from the EcoMeter

Support for additional Legrand energy devices may be added in future releases.

---

## Requirements

- Home Assistant 2026.7 or newer
- Compatible with the Python version bundled with the supported Home Assistant releases.
- A Legrand EcoMeter linked to a Home + Control / Netatmo account
- A Netatmo developer application (OAuth2)

---

## Installation

### HACS

1. Open **HACS**
2. Go to **Integrations**
3. Open the **⋮** menu
4. Select **Custom repositories**
5. Add:

```text
https://github.com/minimicro34/ha-legrand-energy
```

Category:

```text
Integration
```

6. Install **Legrand Energy**
7. Restart Home Assistant

---

## Configuration

### Public API

Create a Netatmo developer application and obtain a Client ID and Client Secret.

These credentials are required only during the initial setup.

When adding the integration, Home Assistant automatically guides you through the OAuth2 authentication process using your **Client ID** and **Client Secret**.

### Private API

Some advanced features require authentication against the Netatmo web services.

The integration securely stores your Netatmo credentials and automatically maintains the private authentication session required to retrieve:

- Electricity contract
- Detailed energy measurements
- Peak / Off-peak tariff data
- Cost calculations
- Consumption projections

No manual extraction of cookies or authentication tokens is required.

Credentials are stored using Home Assistant's secure storage facilities.

---

## Available entities

### Main EcoMeter

#### Energy

- Energy today
- Peak energy today
- Off-peak energy today
- Energy this week
- Energy this month
- Energy this year

#### Costs

- Cost today
- Peak cost today
- Off-peak cost today
- Cost this week
- Cost this month
- Cost this year

#### Projections

- Projected energy today
- Projected energy this month
- Projected energy this year
- Projected cost today
- Projected cost this month
- Projected cost this year

#### Contract

- Contract type
- Tariff option
- Subscribed power
- Peak price
- Off-peak price
- Current tariff
- Current electricity price
- Next tariff change

### Individual circuits

Each electrical circuit exposes:

- Energy today
- Peak energy today
- Off-peak energy today
- Cost today
- Peak cost today
- Off-peak cost today

---

## API rate limits

The Netatmo APIs may occasionally return temporary errors or rate-limit responses.

To improve reliability, historical measurements are cached in memory and refreshed only when necessary (startup, day change, or after a retry delay following a temporary failure). Current-day measurements continue to refresh normally.

The integration preserves the last successfully retrieved values while waiting for the private API to recover, avoiding unnecessary entity unavailability and significantly reducing unnecessary calls to the Netatmo private endpoints.

Electricity contract information is cached and refreshed periodically to reduce unnecessary requests.

---

## Private authentication

The integration automatically refreshes the private Netatmo authentication session while it remains valid.

No manual renewal of cookies, WebTokens or other authentication values is required.

---

## Roadmap

- Water measurements
- Gas measurements
- Additional Legrand energy devices
- Additional diagnostics

---

## Screenshots

*Coming soon.*

---

## Development

Development instructions and contribution guidelines are available in [CONTRIBUTING.md](CONTRIBUTING.md).

Common commands:

```bash
make format
make check
make clean
```

`make check` runs the same quality checks as the GitHub CI workflow.

---

## Contributing

Contributions are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

Please open an Issue before submitting a Pull Request for significant changes.

For security vulnerabilities, please refer to [SECURITY.md](SECURITY.md).

---

## Disclaimer

This project is **not affiliated with, endorsed by, or supported by Legrand or Netatmo**.

It uses official public APIs together with undocumented endpoints required to provide additional energy features. Those undocumented endpoints may change without notice.

---

## Support

Please use GitHub Issues for bug reports and feature requests.

When reporting an issue, always attach diagnostics generated by Home Assistant whenever possible.

## License

MIT
