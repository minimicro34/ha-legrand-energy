"""Pytest bootstrap for local tests without Home Assistant installed."""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = ROOT / "custom_components" / "legrand_energy"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

legrand_energy = types.ModuleType("custom_components.legrand_energy")
legrand_energy.__path__ = [str(DOMAIN_PATH)]
sys.modules.setdefault("custom_components.legrand_energy", legrand_energy)
