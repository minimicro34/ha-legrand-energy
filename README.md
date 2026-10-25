# Legrand Energy

> Bring your Legrand with Netatmo EcoMeter into Home Assistant with native electricity, water, gas and cost monitoring, including interval-average electrical power (not instantaneous readings).

<p align="center">

[![GitHub Release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![CI](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml/badge.svg)](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/ci.yml)
[![Hassfest](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/hassfest.yml/badge.svg)](https://github.com/minimicro34/ha-legrand-energy/actions/workflows/hassfest.yml)
[![HACS](https://img.shields.io/badge/HACS-Custom-blue.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.7%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-☕-FFDD00?logo=buymeacoffee&logoColor=000000)](https://buymeacoffee.com/minimicro34)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE)

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
- 🔄 Native Config Flow and reconfiguration
- 🔐 OAuth2 authentication and reauthentication
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
- A Legrand EcoMeter linked to a Netatmo / Legrand Home + Control account
- A Netatmo developer application with a Client ID and Client Secret

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

Legrand Energy uses two separate authentication mechanisms:

- **Netatmo OAuth2** for the official public API
- **Netatmo / Home + Control account credentials** for private energy and contract data

### Netatmo developer application

Create a Netatmo developer application at:

https://dev.netatmo.com/apps/

Create a new application and obtain its:

- **Client ID**
- **Client Secret**

Leave the following fields empty:

- **Redirect URI**
- **Webhook URI**

No manual token generation is required.

### Application credentials

Legrand Energy uses Home Assistant's native **Application Credentials** support for the Netatmo OAuth2 Client ID and Client Secret.

In Home Assistant:

1. Go to **Settings → Devices & services**
2. Open the **⋮** menu
3. Select **Application credentials**
4. Add credentials for **Legrand Energy**
5. Enter the Client ID and Client Secret from your Netatmo developer application

When adding Legrand Energy, Home Assistant will use these credentials and guide you through the Netatmo OAuth2 authorization process.

OAuth access and refresh tokens are managed automatically by Home Assistant.

If the Netatmo OAuth authorization becomes invalid, Home Assistant will automatically start a reauthentication flow.

### Home + Control authentication

During initial setup, Legrand Energy also asks for the email address and password of your Netatmo / Legrand Home + Control account.

These credentials are used to establish the private authentication session required for data that is not available through the public API alone, including:

- Electricity contract
- Detailed energy measurements
- Peak / Off-peak tariff data
- Cost calculations
- Consumption projections
- Water and gas measurements when available

No browser extensions, cookie extraction, WebToken extraction or manual token management is required.

### Changing credentials

The two authentication mechanisms are managed separately.

To change your **Home + Control email address or password**:

1. Go to **Settings → Devices & services**
2. Open **Legrand Energy**
3. Select **Reconfigure**
4. Enter the new email address and password

Legrand Energy validates the new credentials, creates a new private authentication session and reloads the integration automatically.

The **Netatmo OAuth Client ID and Client Secret** are managed by Home Assistant under **Application credentials**, rather than through the Legrand Energy reconfiguration form.

---

## Bundled Lovelace card

The optional **Legrand Energy** card is shipped in this integration's release.
It does not require a second HACS repository.

1. Restart Home Assistant after installing or updating the integration.
2. For storage-managed dashboards, the integration **automatically registers**
   the JavaScript module resource `/legrand_energy/legrand-energy-card.js`.
   Check **Settings → Dashboards → Resources** before adding anything manually.
   If the resource is absent (for example with YAML-managed Lovelace
   resources), add that URL as a **JavaScript module** once.
3. Add a **Manual** card to a dashboard, using the entity IDs from your installation:

```yaml
type: custom:legrand-energy-card
title: Legrand Energy
entity: sensor.your_energy_today
power_entity: sensor.your_average_power
cost_entity: sensor.your_cost_today
tariff_entity: sensor.your_current_tariff
```

The `entity` field is required; the other fields are optional. The card
provides a summary (including interval-average power, not instantaneous power), period charts (**Day**, **Week**, **Month**, **Year**),
HP/HC breakdown from Home Assistant Recorder statistics, and collapsible
**Circuits** and **Diagnostics** sections. It does not create or modify
energy entities. Use your actual entity IDs, which depend on the discovered
installation.

The **Day** chart uses 30-minute bars when five-minute Recorder statistics
are available and falls back to hourly statistics otherwise. If Recorder
samples are missing, the corresponding energy is displayed in a separate
gray **N/R** (not allocated to a time slot) bar rather than assigned to an
arbitrary half-hour. The footer distinguishes allocated bars, N/R energy,
the current-day Legrand total, and the remaining difference.

The **Year** chart keeps all twelve calendar months visible. Months without
sufficient Recorder history are left blank, not shown as zero. The first
recorded month can be reconstructed from daily Recorder statistics when a
pre-month baseline and sufficient end-of-month evidence exist. Otherwise,
it remains blank rather than displaying an incomplete total. The ongoing
month is handled separately.

The chart uses Home Assistant's existing statistics; it does not import or
reconstruct historical measurements that Recorder never stored.

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

Legrand Energy automatically manages the private Netatmo / Home + Control authentication session.

The integration stores the authentication data in the Home Assistant config entry and automatically renews the private session when required.

No manual renewal of cookies, WebTokens or other private authentication values is required.

If your Home + Control account credentials change, use the integration's **Reconfigure** action to authenticate again.

---

## Roadmap

- Support for additional Legrand energy devices
- Additional diagnostics
- Fluid consumption projections

---

## Screenshots

The following screenshots are reserved for the bundled Lovelace card.
Images will be added after the final visual review of the 1.3.0 beta.

### Day view

<!-- TODO: Add screenshot: screenshots/card-day.png -->
*Screenshot pending — 30-minute energy bars, HP/HC breakdown, daylight-saving transition and separate “N/R” unallocated-energy bar.*

### Month view

<!-- TODO: Add screenshot: screenshots/card-month.png -->
*Screenshot pending — daily energy bars for the current month.*

### Year view

<!-- TODO: Add screenshot: screenshots/card-year.png -->
*Screenshot pending — monthly totals and HP/HC breakdown, including the first available month and current partial month.*

### Circuits

<!-- TODO: Add screenshot: screenshots/card-circuits.png -->
*Screenshot pending — expanded Circuits section with the discovered EcoMeter circuits.*

### Diagnostics

<!-- TODO: Add screenshot: screenshots/card-diagnostics.png -->
*Screenshot pending — expanded diagnostic section with non-sensitive status information. Redact identifiers and tokens before sharing.*

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

`make check` runs the complete local validation pipeline
(compile, formatting, linting, type checking and tests),
matching the GitHub CI workflow.

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

If you find Legrand Energy useful and would like to support its development, you can buy me a coffee.

<p align="center">
  <a href="https://buymeacoffee.com/minimicro34">
    <img
      src="https://github.com/appcraftstudio/buymeacoffee/raw/master/Images/snapshot-bmc-button.png"
      alt="Buy Me a Coffee"
      width="300"
    />
  </a>
</p>

Your support helps me dedicate more time to improving the integration, adding new features and fixing issues.

Bug reports, feature suggestions, contributions and GitHub stars are also greatly appreciated.

Please use GitHub Issues for bug reports and feature requests.

When reporting an issue, always attach diagnostics generated by Home Assistant whenever possible.

Please include the integration version, Home Assistant version and diagnostics whenever possible.

## License

Copyright (c) 2026 minimicro34

This project is licensed under the [GNU General Public License v3.0 or later](LICENSE).
