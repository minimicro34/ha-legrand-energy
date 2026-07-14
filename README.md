# Legrand Energy

[![GitHub release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE)

Home Assistant custom integration for the **Legrand EcoMeter** ecosystem using **Home + Control / Netatmo** services.

The integration discovers the EcoMeter installation and its electrical circuits, retrieves energy measurements, exposes electricity contract information, and calculates tariff-based consumption, costs, and projections.

> ⚠️ This project is under active development and uses both public and undocumented private APIs.

---

# Features

## Integration

- Home Assistant Config Flow
- Options Flow for private API authentication
- HACS compatible
- Automatic device and circuit discovery
- Home Assistant Device Registry integration
- Coordinator-based polling
- Diagnostics support

## Authentication

- OAuth2 authentication for the public API
- Automatic OAuth access token refresh
- Private Netatmo API authentication
- Automatic private WebToken refresh while the Netatmo web session remains valid
- Persistent authentication data
- API rate-limit handling with cached data preservation

## EcoMeter discovery

- Automatic EcoMeter installation discovery
- Automatic electrical circuit discovery
- Main EcoMeter device
- Individual circuit devices
- Module type information
- Room information
- Installation date

## Energy measurements

### Main EcoMeter

- Consumption today
- Peak-hours consumption today
- Off-peak-hours consumption today
- Cost today
- Peak-hours cost today
- Off-peak-hours cost today
- Daily cost projection
- Monthly cost projection

### Individual circuits

- Consumption today
- Peak-hours consumption today
- Off-peak-hours consumption today
- Cost today
- Peak-hours cost today
- Off-peak-hours cost today

## Electricity contract

- Contract type
- Tariff option
- Subscribed power
- Peak-hours price
- Off-peak-hours price
- Current tariff period
- Current electricity price
- Next tariff change

Tariff information is calculated automatically from the electricity contract timetable.

## Diagnostics

Diagnostic entities include installation and module information such as:

- Installation date
- Room
- Module type

The main EcoMeter device also exposes electricity contract information as diagnostic entities.

---

# Installation

## HACS

1. Open **HACS**
2. Go to **Integrations**
3. Open the three-dot menu
4. Select **Custom repositories**
5. Add:

```text
https://github.com/minimicro34/ha-legrand-energy
```

Category:

```text
Integration
```

6. Download **Legrand Energy**
7. Restart Home Assistant

---

# Configuration

## Public API

Create a Legrand / Netatmo developer application and retrieve:

- Client ID
- Client Secret
- Access Token
- Refresh Token

Then add the integration from:

**Settings → Devices & Services → Add Integration → Legrand Energy**

## Private API

Some advanced features require authentication data from the Netatmo / Home + Control web session.

These values can be configured from the integration options:

- Web Token
- Web Refresh Token
- Laravel Session
- Mail Cookie
- Authorize State
- XSRF Token

The private API is currently used for features including:

- Electricity contract retrieval
- Detailed electricity measurements
- Peak / off-peak calculations
- Cost calculations
- Cost projections

> ⚠️ The private API is undocumented and may change without notice.

---

# Supported devices

- ✅ Legrand EcoMeter / connected energy monitoring installations exposed through Home + Control / Netatmo
- ✅ Individual electrical circuits discovered from the EcoMeter installation

Support for additional Legrand energy devices may be added in future releases.

---

# Current status

| Feature | Status |
|----------|--------|
| Home Assistant Config Flow | ✅ |
| Options Flow | ✅ |
| Public OAuth authentication | ✅ |
| Public OAuth token refresh | ✅ |
| Private API authentication | ✅ |
| Private WebToken refresh | ✅ |
| EcoMeter discovery | ✅ |
| Circuit discovery | ✅ |
| Device Registry | ✅ |
| Daily energy measurements | ✅ |
| Peak / off-peak measurements | ✅ |
| Cost calculations | ✅ |
| Cost projections | ✅ |
| Electricity contract information | ✅ |
| Tariff schedule | ✅ |
| Diagnostics | ✅ |
| API rate-limit handling | ✅ |
| HACS | ✅ |
| Instantaneous power | 🚧 |
| Water measurements | 🚧 |
| Gas measurements | 🚧 |

---

# API rate limits

The Netatmo APIs may return rate-limit errors.

The integration includes handling for API rate limits and attempts to preserve the last successfully retrieved data instead of immediately making entities unavailable.

Electricity contract data is cached and refreshed periodically to reduce unnecessary private API requests.

---

# Private WebToken refresh

The integration can automatically refresh the private Netatmo WebToken while the associated web session remains valid.

The refresh mechanism uses the existing Netatmo authentication session and preserves the refreshed WebToken for subsequent requests.

Because this mechanism relies on an undocumented Netatmo web authentication flow, changes to the Netatmo website may affect this functionality.

---

# Roadmap

- Instantaneous power measurements
- Energy Dashboard improvements
- Water measurements
- Gas measurements
- Additional Legrand energy devices
- Improved private API authentication
- Additional diagnostics
- Additional historical statistics

---

# Screenshots

Coming soon.

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
- Legrand Energy integration version
- Relevant diagnostic information
- Relevant logs with authentication tokens and private cookies removed

> ⚠️ Never publish access tokens, refresh tokens, WebTokens, session cookies, or other authentication credentials in an Issue.

---

# Disclaimer

This project is **not affiliated with, endorsed by, or supported by Legrand or Netatmo**.

It uses public APIs and undocumented API endpoints discovered through reverse engineering for interoperability purposes.

Undocumented APIs may change or stop working without notice.

---

# License

MIT