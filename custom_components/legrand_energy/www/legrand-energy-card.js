/* Legrand Energy Lovelace card — bundled with the integration. */
class LegrandEnergyCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.trim()) {
      throw new Error("Legrand Energy: an energy entity is required");
    }
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return { entity: "" };
  }

  _render() {
    if (!this._config) return;
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this.appendChild(this._card);
    }
    this._card.replaceChildren();
    const wrapper = document.createElement("div");
    wrapper.style.padding = "16px";
    const title = document.createElement("h2");
    title.style.margin = "0 0 12px";
    title.textContent = this._config.title || "Legrand Energy";
    wrapper.appendChild(title);
    const fields = [
      ["Énergie aujourd'hui", this._config.entity],
      ["Puissance moyenne", this._config.power_entity],
      ["Coût aujourd'hui", this._config.cost_entity],
      ["Tarif actuel", this._config.tariff_entity],
    ];
    for (const [label, entityId] of fields) {
      if (!entityId) continue;
      const state = this._hass?.states?.[entityId];
      const row = document.createElement("div");
      row.style.cssText = "display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-bottom:1px solid var(--divider-color)";
      const name = document.createElement("span");
      name.textContent = label;
      const value = document.createElement("strong");
      value.textContent = state && !["unknown", "unavailable"].includes(state.state)
        ? state.state + (state.attributes?.unit_of_measurement ? " " + state.attributes.unit_of_measurement : "")
        : "—";
      row.append(name, value);
      wrapper.appendChild(row);
    }
    this._card.appendChild(wrapper);
  }
}
if (!customElements.get("legrand-energy-card")) {
  customElements.define("legrand-energy-card", LegrandEnergyCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "legrand-energy-card")) {
  window.customCards.push({
    type: "legrand-energy-card",
    name: "Legrand Energy",
    description: "Legrand EcoMeter energy, average power, cost and tariff summary",
  });
}
