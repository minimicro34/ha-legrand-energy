# Legrand Energy

> Bring your Legrand with Netatmo EcoMeter into Home Assistant with native electricity, water, gas and cost monitoring.

<p align="center">

[![GitHub Release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![CI](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml/badge.svg)](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml)
[![HACS](https://img.shields.io/badge/HACS-Default-blue.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.7%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE.md)

</p>

⚡ Electricity • 💧 Water • 🔥 Gas • 💶 Costs • 📈 Projections

---

Legrand Energy is a custom Home Assistant integration for the **Legrand with Netatmo EcoMeter**.

It automatically discovers your electrical, water and gas circuits and provides native Home Assistant entities for:

- ⚡ Electricity consumption
- 💧 Water consumption
- 🔥 Gas consumption
- 💶 Cost monitoring
- 📈 Consumption projections
- 🔌 Per-circuit monitoring
- 🏠 Contract and tariff information

> **Note**
>
> This integration uses both the official Legrand APIs and the private Home + Control API to expose data that is not available through the public API alone.

---

## Contents

- [Features](#features)
- [Known limitations](#known-limitations)
- [Supported devices](#supported-devices)
- [Compatibility](#compatibility)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Available entities](#available-entities)
- [API rate limits](#api-rate-limits)
- [Private authentication](#private-authentication)
- [Roadmap](#roadmap)
- [Screenshots](#screenshots)
- [Development](#development)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [Support](#support)
- [License](#license)

---

## Features

### Energy and fluid monitoring

- ⚡ Automatic EcoMeter and electrical circuit discovery
- 📊 Daily, weekly, monthly and yearly electricity consumption
- 💶 Electricity cost calculation
- 📈 Electricity consumption and cost projections
- 🔌 Per-circuit electricity and cost monitoring
- 💧 Cold and hot water consumption monitoring
- 🔥 Gas consumption monitoring
- 💶 Water and gas cost monitoring (when supported by Home + Control)

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
- Water and gas cost entities depend on the information returned by Home + Control.
- Some installations expose consumption data but do not provide fluid pricing. In this case, the corresponding cost entities remain unavailable.
- Fluid measurements may remain unavailable when no consumption history exists in Home + Control.

---

## Supported devices

Currently tested with:

- ✅ Legrand EcoMeter
- ✅ Home + Control / Netatmo energy installations
- ✅ Electrical circuits discovered from the EcoMeter
- ✅ Cold water circuits exposed by the EcoMeter
- ✅ Hot water circuits exposed by the EcoMeter
- ✅ Gas circuits exposed by the EcoMeter

Support for additional Legrand energy devices may be added in future releases.

---

## Compatibility

| Component | Supported |
|-----------|-----------|
| Home Assistant | ✅ |
| HACS | ✅ |
| Home + Control | ✅ |
| Legrand EcoMeter | ✅ |
| Electricity | ✅ |
| Water | ✅ |
| Gas | ✅ |

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

No browser extensions, cookie extraction or manual token management is required.

Some advanced features require authentication against the Netatmo web services.

The integration securely stores your Netatmo credentials and automatically maintains the private authentication session required to retrieve:

- Electricity contract
- Detailed energy measurements
- Peak / Off-peak tariff data
- Cost calculations
- Consumption projections

Credentials are stored using Home Assistant's secure storage facilities.

---

## Available entities

### Main EcoMeter

### Energy

- Energy today
- Peak energy today
- Off-peak energy today
- Energy this week
- Energy this month
- Energy this year

### Costs

- Cost today
- Peak cost today
- Off-peak cost today
- Cost this week
- Cost this month
- Cost this year

### Projections

- Projected energy today
- Projected energy this month
- Projected energy this year
- Projected cost today
- Projected cost this month
- Projected cost this year

### Contract

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

### Water circuits

Each cold or hot water circuit exposes:

- Consumption today
- Consumption this week
- Consumption this month
- Consumption this year

When Home + Control provides water pricing information, the following entities are also available:

- Cost today
- Cost this week
- Cost this month
- Cost this year

### Gas circuits

Each gas circuit exposes:

- Consumption today
- Consumption this week
- Consumption this month
- Consumption this year

When Home + Control provides gas pricing information, the following entities are also available:

- Cost today
- Cost this week
- Cost this month
- Cost this year

Home + Control reports gas consumption in dm³. Since 1 dm³ equals 1 litre, the integration exposes gas consumption in litres for Home Assistant compatibility.

---

## API rate limits

The Netatmo APIs may occasionally return temporary errors or rate-limit responses.

To improve reliability, historical measurements are cached in memory and refreshed only when necessary (startup, day change, or after a retry delay following a temporary failure). Current-day measurements automatically use a progressive retry backoff after temporary failures while continuing to expose the last successfully retrieved values.

The integration preserves the last successfully retrieved values while waiting for the private API to recover, avoiding unnecessary entity unavailability and significantly reducing unnecessary calls to the Netatmo private endpoints.

Electricity contract information is cached and refreshed periodically to reduce unnecessary requests.

---

## Private authentication

The integration automatically refreshes the private Netatmo authentication session while it remains valid.

No manual renewal of cookies, WebTokens or other authentication values is required.

---

## Roadmap

- Support for additional Legrand energy devices
- Additional diagnostics
- Fluid consumption projections

---

## Screenshots

Screenshots will be added once the integration reaches feature completeness.

---

## Development

Development instructions and contribution guidelines are available in [CONTRIBUTING.md](CONTRIBUTING.md).

Common commands:

```bash
make compile
make format
make format-check
make lint
make typecheck
make test
make check
make clean
```

`make check` runs the complete local validation pipeline (compile, formatting, linting, type checking, tests and Git working tree checks), matching the GitHub CI workflow.

---

## Contributing

Contributions are welcome.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting changes.

Please open an Issue before submitting a Pull Request for significant changes.

⚠️ **Never publish authentication credentials, cookies, access tokens, refresh tokens, or private API secrets.**

---

## Disclaimer

This project is **not affiliated with, endorsed by, or supported by Legrand or Netatmo**.

It uses official public APIs together with undocumented endpoints required to provide additional energy features. Those undocumented endpoints may change without notice.

---

## Support

Please use GitHub Issues for bug reports and feature requests.

When reporting an issue, always attach diagnostics generated by Home Assistant whenever possible.

Please include the integration version, Home Assistant version and diagnostics whenever possible.

## License

MIT
