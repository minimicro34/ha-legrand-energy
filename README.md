# Legrand Energy

[![GitHub release](https://img.shields.io/github/v/release/minimicro34/ha-legrand-energy)](https://github.com/minimicro34/ha-legrand-energy/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![License](https://img.shields.io/github/license/minimicro34/ha-legrand-energy)](LICENSE)

Home Assistant integration for the **Legrand EcoMeter** (Home + Control / Netatmo).

> ⚠️ This project is under active development.

---

# Features

- OAuth2 authentication
- Automatic token refresh
- Automatic discovery of EcoMeter installations
- Automatic discovery of electrical circuits
- Home Assistant Config Flow
- HACS compatible

---

# Installation

## HACS

1. Open **HACS**
2. Integrations
3. Three dots → **Custom repositories**
4. Add:

```
https://github.com/minimicro34/ha-legrand-energy
```

Category:

```
Integration
```

Restart Home Assistant.

---

# Configuration

Create a Legrand / Netatmo application and retrieve:

- Client ID
- Client Secret
- Access Token
- Refresh Token

Then add the integration from:

Settings → Devices & Services → Add Integration

---

# Supported devices

- ✅ Legrand EcoMeter

---

# Current status

| Feature | Status |
|----------|--------|
| OAuth | ✅ |
| Auto Refresh Token | ✅ |
| Device Discovery | ✅ |
| Circuit Discovery | ✅ |
| HACS | ✅ |
| Diagnostics | 🚧 |
| Live Measurements | 🚧 |

---

# Roadmap

- Device Registry
- Diagnostics
- Energy Dashboard support
- Live measurements
- Contract information
- Water and gas measurements

---

# Screenshots

Coming soon.

---

# Contributing

Contributions are welcome.

Please open an Issue before submitting a Pull Request.

---

# Disclaimer

This project is **not affiliated with Legrand or Netatmo**.

It uses publicly available APIs and reverse engineering for interoperability.

---

# License

MIT