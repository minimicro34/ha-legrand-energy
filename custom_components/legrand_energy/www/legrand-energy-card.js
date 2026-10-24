/* Legrand Energy Lovelace card — bundled with the integration. */
class LegrandEnergyCard extends HTMLElement {
  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.trim()) {
      throw new Error("Legrand Energy: an energy entity is required");
    }
    this._config = { ...config };
    this._period = this._period || "day";
    this._history = null;
    this._historyKey = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
    this._loadHistory();
  }

  getCardSize() { return 7; }
  getGridOptions() { return { columns: 12, min_columns: 6 }; }
  static getStubConfig() { return { entity: "" }; }

  _state(id) {
    const state = this._hass?.states?.[id];
    return state && !["unknown", "unavailable"].includes(state.state)
      ? state : null;
  }

  _value(id, digits = 2) {
    const state = this._state(id);
    if (!state) return "—";
    const number = Number(state.state);
    const value = Number.isFinite(number)
      ? new Intl.NumberFormat(this._hass?.locale?.language || "fr-FR", {
          maximumFractionDigits: digits,
        }).format(number)
      : state.state;
    return value + (state.attributes?.unit_of_measurement
      ? " " + state.attributes.unit_of_measurement : "");
  }

  _nextTariffChange() {
    const id = this._autoEntity(this._config.next_tariff_change_entity,
      ["prochain_changement_de_tarif"], "next_tariff_change");
    const raw = this._state(id)?.state;
    if (!raw) return null;
    const date = new Date(raw);
    if (!Number.isFinite(date.getTime())) return raw;
    return new Intl.DateTimeFormat(this._hass?.locale?.language || "fr-FR", {
      hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit",
    }).format(date);
  }

  _element(tag, text, css) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (css) el.style.cssText = css;
    return el;
  }

  _row(label, value) {
    const row = this._element("div", undefined,
      "display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid var(--divider-color)");
    row.title = label + " : " + value;
    row.append(this._element("span", label), this._element("strong", value));
    return row;
  }

  _autoEntity(explicit, suffixes, registryKey) {
    if (explicit) return explicit;
    const base = this._config?.entity || "";
    const entities = this._hass?.entities;
    const anchor = entities?.[base];
    // Registry unique IDs are stable across renames and translations.
    // Restrict matches to the exact EcoMeter module of the selected entity.
    if (anchor?.unique_id?.endsWith("_energy_today") && registryKey) {
      const moduleId = anchor.unique_id.slice(0, -"_energy_today".length);
      const matches = Object.values(entities).filter((entry) =>
        entry.platform === "legrand_energy" &&
        entry.unique_id === moduleId + "_" + registryKey &&
        this._hass?.states?.[entry.entity_id]
      );
      if (matches.length === 1) return matches[0].entity_id;
      // Never guess by translated entity names when registry metadata exists.
      return null;
    }
    // Compatibility fallback for older HA frontends without registry metadata.
    const prefix = base.replace(/consommation_aujourd_hui$/, "");
    if (prefix === base) return null;
    for (const suffix of suffixes) {
      const id = prefix + suffix;
      if (this._hass?.states?.[id]) return id;
    }
    return null;
  }

  _periodEntity() {
    const c = this._config;
    return {
      day: c.entity,
      week: this._autoEntity(c.week_entity, ["energie"], "energy_week"),
      month: this._autoEntity(c.month_entity, ["energie_2"], "energy_month"),
      year: this._autoEntity(c.year_entity, ["energie_3"], "energy_year"),
    }[this._period];
  }

  _dateRange() {
    const now = new Date();
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);
    if (this._period === "week") {
      start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    } else if (this._period === "month") {
      start.setDate(1);
    } else if (this._period === "year") {
      start.setMonth(0, 1);
    }
    return { start, end: now };
  }

  async _loadHistory() {
    if (!this._hass?.callWS || !this._config) return;
    const entity = this._periodEntity();
    if (!entity) return;
    const { start, end } = this._dateRange();
    const key = [entity, this._period, start.toISOString()].join("|");
    if (key === this._historyKey) return;
    this._historyKey = key;
    this._history = null;
    this._historyError = false;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "history/history_during_period",
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        entity_ids: [entity],
        minimal_response: true,
        no_attributes: true,
      });
      if (this._historyKey !== key) return;
      this._history = Array.isArray(result) ? (result[0] || []) : [];
    } catch (_error) {
      if (this._historyKey !== key) return;
      this._history = [];
      this._historyError = true;
    }
    this._render();
  }

  _chart() {
    const box = this._element("div");
    const points = (this._history || []).map((item) => ({
      time: typeof item.lu === "number" ? item.lu * 1000 : Date.parse(item.last_changed || item.last_updated || item.lu),
      value: Number(item.state ?? item.s),
    })).filter((point) => Number.isFinite(point.time) && Number.isFinite(point.value));
    if (!points.length) {
      box.appendChild(this._element("div",
        this._history === null ? "Chargement de l'historique…" : this._historyError ? "Historique indisponible (requête Home Assistant en échec)." : "Aucun historique disponible pour cette période.",
        "padding:24px 0;color:var(--secondary-text-color);text-align:center"));
      return box;
    }
    const { start, end } = this._dateRange();
    const min = Math.min(0, ...points.map((point) => point.value));
    const max = Math.max(1, ...points.map((point) => point.value));
    const x = (time) => 10 + 580 * (time - start.getTime()) / Math.max(1, end.getTime() - start.getTime());
    const y = (value) => 135 - 120 * (value - min) / Math.max(0.001, max - min);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 600 150");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Historique de consommation");
    svg.style.cssText = "width:100%;height:auto;display:block";
    const path = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    path.setAttribute("points", points.map((point) => x(point.time) + "," + y(point.value)).join(" "));
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "var(--primary-color)");
    path.setAttribute("stroke-width", "2.5");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.appendChild(path);
    box.appendChild(svg);
    box.appendChild(this._element("div",
      "Historique du compteur · " + points.length + " mesures",
      "font-size:12px;color:var(--secondary-text-color);text-align:right"));
    return box;
  }

  _render() {
    if (!this._config) return;
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this.appendChild(this._card);
    }
    this._card.replaceChildren();
    const wrapper = this._element("div", undefined, "padding:16px");
    wrapper.appendChild(this._element("h2", this._config.title || "Legrand Energy",
      "margin:0 0 12px"));

    const metrics = this._element("div", undefined,
      "display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-bottom:16px");
    for (const [label, id, digits] of [
      ["Énergie aujourd'hui", this._config.entity, 3],
      ["Puissance moyenne", this._config.power_entity, 0],
      ["Coût aujourd'hui", this._config.cost_entity, 2],
      ["Tarif actuel", this._config.tariff_entity, 2],
    ]) {
      if (!id) continue;
      const tile = this._element("div", undefined,
        "padding:12px;border:1px solid var(--divider-color);border-radius:10px;min-width:0");
      tile.title = label + " · " + (id || "Capteur non configuré") + " · " + this._value(id, digits);
      tile.append(this._element("div", label,
        "font-size:12px;color:var(--secondary-text-color)"),
        this._element("div", this._value(id, digits),
          "font-size:20px;font-weight:600;overflow-wrap:anywhere"));
      metrics.appendChild(tile);
    }
    wrapper.appendChild(metrics);
    const tariff = this._state(this._config.tariff_entity)?.state;
    const nextChange = this._nextTariffChange();
    if (tariff || nextChange) {
      const line = this._element("div", undefined,
        "display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:10px 12px;margin-bottom:14px;border:1px solid var(--divider-color);border-radius:10px");
      line.appendChild(this._element("strong",
        tariff === "HP" ? "Heures pleines (HP)" : tariff === "HC" ? "Heures creuses (HC)" : tariff || "Tarif en cours"));
      if (nextChange) line.appendChild(this._element("span", "Prochain changement : " + nextChange));
      wrapper.appendChild(line);
    }

    const tabs = this._element("div", undefined,
      "display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap");
    for (const [period, label] of [
      ["day", "Jour"], ["week", "Semaine"],
      ["month", "Mois"], ["year", "Année"],
    ]) {
      const button = this._element("button", label,
        "border:1px solid var(--divider-color);border-radius:8px;padding:7px 12px;cursor:pointer;background:" +
        (this._period === period ? "var(--primary-color)" : "var(--card-background-color)") +
        ";color:" + (this._period === period ? "white" : "var(--primary-text-color)"));
      button.addEventListener("click", () => {
        this._period = period;
        this._historyKey = null;
        this._history = null;
        this._render();
        this._loadHistory();
      });
      tabs.appendChild(button);
    }
    wrapper.appendChild(tabs);
    const periodEntity = this._periodEntity();
    wrapper.appendChild(this._row("Consommation " +
      { day: "du jour", week: "de la semaine", month: "du mois", year: "de l'année" }[this._period],
      periodEntity ? this._value(periodEntity, 3) : "Capteur non configuré"));
    if (periodEntity) wrapper.appendChild(this._chart());

    const circuits = this._config.circuits;
    if (Array.isArray(circuits) && circuits.length) {
      const details = this._element("details", undefined, "margin-top:16px");
      details.appendChild(this._element("summary", "Circuits",
        "cursor:pointer;font-weight:600;padding:8px 0"));
      for (const circuit of circuits) {
        if (!circuit || !circuit.entity) continue;
        details.appendChild(this._row(circuit.name || circuit.entity,
          this._value(circuit.entity)));
      }
      wrapper.appendChild(details);
    }

    const diagnostics = [
      ["Puissance souscrite", this._autoEntity(this._config.subscribed_power_entity, ["puissance_souscrite"], "contract_power")],
      ["Option tarifaire", this._autoEntity(this._config.tariff_option_entity, ["option_tarifaire"], "contract_option")],
      ["Prix actuel", this._autoEntity(this._config.current_price_entity, ["prix_actuel"], "current_price")],
      ["Prix heures pleines", this._autoEntity(this._config.peak_price_entity, ["prix_heures_pleines"], "peak_price")],
      ["Prix heures creuses", this._autoEntity(this._config.offpeak_price_entity, ["prix_heures_creuses"], "off_peak_price")],
      ["Prochain changement", this._autoEntity(this._config.next_tariff_change_entity, ["prochain_changement_de_tarif"], "next_tariff_change")],
      ["Type de contrat", this._autoEntity(this._config.contract_entity, ["type_de_contrat"], "contract_type")],
    ].filter((item) => item[1]);
    if (diagnostics.length) {
      const details = this._element("details", undefined, "margin-top:16px");
      details.appendChild(this._element("summary", "Contrat et diagnostics",
        "cursor:pointer;font-weight:600;padding:8px 0"));
      for (const [label, id] of diagnostics) {
        details.appendChild(this._row(label, label === "Prochain changement" ? (this._nextTariffChange() || "—") : this._value(id)));
      }
      wrapper.appendChild(details);
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
    description: "Legrand EcoMeter consumption history, circuits and tariff details",
  });
}
