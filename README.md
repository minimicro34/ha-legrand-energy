# Legrand Energy for Home Assistant

[![GitHub release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE)

A Home Assistant custom integration for **Legrand EcoMeter** installations using **Home + Control / Netatmo** services.

The integration automatically discovers your EcoMeter installation and electrical circuits, retrieves energy measurements, calculates electricity costs according to your tariff, and exposes contract information directly in Home Assistant.

> ⚠️ This integration relies on both public and undocumented Netatmo APIs. Some advanced features may stop working if Netatmo changes its web services.

---

# Features

## Supported features

- ⚡ Automatic EcoMeter discovery
- 🔌 Automatic circuit discovery
- 📊 Energy consumption
- 💶 Electricity cost calculation
- 🟢 Peak / Off-peak tariff detection
- 📈 Consumption projections
- 📋 Electricity contract retrieval
- 🔄 Automatic OAuth token refresh
- 🔐 Automatic private session renewal
- 🩺 Diagnostics support

## Integration

- Home Assistant Config Flow
- OAuth2 authentication
- Options Flow
- HACS compatible
- Automatic device discovery
- Device Registry support
- Coordinator-based polling
- Diagnostics support

## Known limitations

- Historical measurements currently start from the first successful synchronization.
- Some advanced features rely on undocumented Netatmo web services.
- Changes to Netatmo private APIs may temporarily affect contract or tariff information.
---

# Supported devices

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
# Installation

## HACS

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

# Configuration

## Public API

Create a Netatmo developer application and obtain a Client ID and Client Secret.

These credentials are required only during the initial setup.

When adding the integration, Home Assistant automatically guides you through the OAuth2 authentication process using your **Client ID** and **Client Secret**.

## Private API

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

# Available entities

## Main EcoMeter

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

## Individual circuits

Each electrical circuit exposes:

- Energy today
- Peak energy today
- Off-peak energy today
- Cost today
- Peak cost today
- Off-peak cost today

---

# API rate limits

The Netatmo APIs may occasionally return rate-limit errors.

The integration preserves the last successfully retrieved values while waiting for the API rate limit to reset, avoiding unnecessary entity unavailability.

Electricity contract information is cached and refreshed periodically to reduce unnecessary requests.

---

# Private authentication

The integration automatically refreshes the private Netatmo authentication session while it remains valid.

No manual renewal of cookies, WebTokens or other authentication values is required.

---

# Roadmap

- Historical statistics
- Instantaneous power
- Water measurements
- Gas measurements
- Additional Legrand energy devices
- Energy Dashboard improvements
- Additional diagnostics

---

# Screenshots

*Coming soon.*

---

# Development

Run the following checks before submitting changes:

```bash
python3.13 -m ruff check .
python3.13 -m ruff format --check .
python3.13 -m mypy custom_components/legrand_energy
python3.13 -m pytest -v
```

---

# Contributing

Contributions are welcome.

Please open an Issue before submitting a Pull Request.

When reporting an issue, include:

- Home Assistant version
- Integration version
- Diagnostic information
- Relevant logs

⚠️ **Never publish authentication credentials, cookies or tokens.**

---

# Disclaimer

This project is **not affiliated with, endorsed by, or supported by Legrand or Netatmo**.

It uses official public APIs together with undocumented endpoints required to provide additional energy features. Those undocumented endpoints may change without notice.

---
# Support

Please use GitHub Issues for bug reports and feature requests.

When reporting an issue, always attach diagnostics generated by Home Assistant whenever possible.

# License

MIT
