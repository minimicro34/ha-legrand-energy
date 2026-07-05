"""Discovery tool for Legrand Energy API."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from ha_legrand_energy.api import LegrandAPI

OUTPUT_DIR = Path("output")


def save_json(name: str, data: dict) -> None:
    """Save JSON to output folder."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"✔ Saved {path}")


async def main() -> None:
    """Main discovery flow."""
    load_dotenv()

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    subscription_key = os.getenv("SUBSCRIPTION_KEY")
    access_token = os.getenv("ACCESS_TOKEN")
    home_id = os.getenv("HOME_ID")

    if not all([subscription_key, access_token]):
        raise RuntimeError("Missing ACCESS_TOKEN or SUBSCRIPTION_KEY in .env")

    print("\n🔌 Initializing API client...\n")

    api = LegrandAPI(
        access_token=access_token,
        subscription_key=subscription_key,
    )

    try:
        # -------------------------
        # 1. Homes
        # -------------------------
        print("🏠 Fetching homesdata...")
        homes = await api.async_get_homesdata()
        save_json("homesdata", homes)

        homes_list = homes.get("body", {}).get("homes", [])
        if not homes_list:
            print("⚠ No homes found")
            return

        home_id = homes_list[0].get("id")
        print(f"✔ Home ID: {home_id}")

        # -------------------------
        # 2. Topology
        # -------------------------
        print("\n🗺 Fetching topology...")
        topology = await api.async_get_hometopology(home_id)
        save_json("topology", topology)

        # -------------------------
        # 3. Status
        # -------------------------
        print("\n📊 Fetching homestatus...")
        status = await api.async_get_homestatus(home_id)
        save_json("homestatus", status)

        # -------------------------
        # 4. Energy
        # -------------------------
        print("\n⚡ Fetching energy data...")
        energy = await api.async_get_energy(home_id)
        save_json("energy", energy)

        print("\n✅ Discovery completed successfully\n")

    finally:
        await api.async_close()


if __name__ == "__main__":
    asyncio.run(main())
