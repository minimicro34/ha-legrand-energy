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
    this._tariffHistory = null;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
    this._loadHistory();
    this._loadEntityRegistry();
  }

  async _loadEntityRegistry() {
    if (!this._hass?.callWS || this._registry || this._registryLoading) return;
    this._registryLoading = true;
    try {
      const entries = await this._hass.callWS({ type: "config/entity_registry/list" });
      if (Array.isArray(entries)) {
        this._registry = Object.fromEntries(entries.map((entry) => [entry.entity_id, entry]));
        this._render();
      }
    } catch (_error) {
      // Manual circuit configuration remains available if registry access fails.
    } finally {
      this._registryLoading = false;
    }
  }

  getCardSize() { return 7; }
  getGridOptions() { return { columns: 36, min_columns: 12 }; }
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
    const entities = this._registry || this._hass?.entities;
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

  _circuits() {
    if (Array.isArray(this._config?.circuits) && this._config.circuits.length) {
      return this._config.circuits;
    }
    const registry = this._registry || this._hass?.entities;
    const anchor = registry?.[this._config?.entity];
    if (!anchor?.unique_id?.endsWith("_energy_today")) return [];
    const moduleId = anchor.unique_id.slice(0, -"_energy_today".length);
    const entries = Object.values(registry).filter((entry) =>
      entry.platform === "legrand_energy" &&
      typeof entry.unique_id === "string" &&
      entry.unique_id.startsWith(moduleId + "#") &&
      entry.unique_id.endsWith("_circuit_energy_today") &&
      this._hass?.states?.[entry.entity_id]
    );
    return entries.map((entry) => {
      const moduleKey = entry.unique_id.slice(0, -"_circuit_energy_today".length);
      const power = Object.values(registry).find((candidate) =>
        candidate.platform === "legrand_energy" &&
        candidate.unique_id === moduleKey + "_circuit_average_power" &&
        this._hass?.states?.[candidate.entity_id]
      );
      const friendly = this._hass.states[entry.entity_id].attributes?.friendly_name;
      return {
        name: entry.name || friendly || entry.entity_id,
        entity: entry.entity_id,
        power_entity: power?.entity_id,
      };
    }).sort((a, b) => a.name.localeCompare(b.name));
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
    const entity = this._config.entity;
    const { start, end } = this._dateRange();
    const period = this._period === "day" ? "hour" :
      this._period === "year" ? "month" : "day";
    // Include the preceding bucket to calculate the first visible delta.
    const queryStart = new Date(start);
    if (period === "hour") queryStart.setHours(queryStart.getHours() - 1);
    else if (period === "month") queryStart.setMonth(queryStart.getMonth() - 1);
    else queryStart.setDate(queryStart.getDate() - 1);
    const key = [entity, this._period, start.toISOString()].join("|");
    if (key === this._historyKey) return;
    this._historyKey = key;
    this._history = null;
    this._historyError = false;
    this._tariffHistory = null;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: queryStart.toISOString(),
        end_time: end.toISOString(),
        statistic_ids: [entity],
        period,
        types: ["sum"],
      });
      if (this._historyKey !== key) return;
      const rows = result?.[entity] || [];
      this._history = rows.map((row, index) => {
        const previous = index ? rows[index - 1] : null;
        const sum = Number(row.sum);
        const before = Number(previous?.sum);
        return {
          time: typeof row.start === "number" ?
            (row.start > 1e11 ? row.start : row.start * 1000) : Date.parse(row.start),
          value: previous && Number.isFinite(before) && Number.isFinite(sum)
            ? Math.max(0, sum - before) : null,
        };
      }).filter((point) => Number.isFinite(point.time) &&
        point.time >= start.getTime() && point.time <= end.getTime() &&
        point.value !== null && Number.isFinite(point.value));
    } catch (_error) {
      if (this._historyKey !== key) return;
      this._history = [];
      this._historyError = true;
    }
    // Historical tariff states are needed: today's current HP/HC state cannot
    // reliably classify earlier hourly consumption.
    if (this._period === "day" && !this._historyError) {
      const tariffEntity = this._autoEntity(this._config.tariff_entity,
        ["tarif_actuel"], "current_tariff");
      if (tariffEntity) {
        try {
          const history = await this._hass.callWS({
            type: "history/history_during_period",
            start_time: start.toISOString(),
            end_time: end.toISOString(),
            entity_ids: [tariffEntity],
            minimal_response: false,
            no_attributes: true,
            significant_changes_only: false,
          });
          if (this._historyKey === key) {
            const entries = (Array.isArray(history) ? history[0] : []) || [];
            this._tariffHistory = entries.map((entry) => ({
              time: Date.parse(entry.last_changed || entry.last_updated),
              state: entry.s === "HP" || entry.state === "HP" ? "HP" :
                entry.s === "HC" || entry.state === "HC" ? "HC" : null,
            })).filter((entry) => Number.isFinite(entry.time))
              .sort((a, b) => a.time - b.time);
          }
        } catch (_error) {
          // The graph remains usable with neutral bars if history is unavailable.
        }
      }
    }
    this._render();
  }

  _hourTariff(time) {
    const entries = this._tariffHistory;
    if (!entries?.length) return null;
    let state = null;
    for (const entry of entries) {
      if (entry.time <= time) state = entry.state;
      else if (entry.time < time + 3600000) return null; // Mixed hour.
      else break;
    }
    return state;
  }

  _chart() {
    const box = this._element("div", undefined, "position:relative");
    const recorded = this._history || [];
    // Keep all twelve calendar months visible; missing statistics are not zero.
    const points = this._period === "year" && recorded.length
      ? Array.from({ length: 12 }, (_, month) => {
        const year = this._dateRange().start.getFullYear();
        const matching = recorded.find((point) => {
          const date = new Date(point.time);
          return date.getFullYear() === year && date.getMonth() === month;
        });
        return matching || { time: new Date(year, month, 1).getTime(), value: null };
      })
      : recorded;
    if (!recorded.length) {
      box.appendChild(this._element("div",
        this._history === null ? "Chargement des statistiques…" :
          this._historyError ? "Statistiques indisponibles (requête Home Assistant en échec)." :
          "Aucune statistique disponible pour cette période.",
        "padding:24px 0;color:var(--secondary-text-color);text-align:center"));
      return box;
    }
    const locale = this._hass?.locale?.language || "fr-FR";
    const width = 800, height = 230, left = 56, right = 12, top = 18, bottom = 46;
    const plotHeight = height - top - bottom;
    const max = Math.max(0.001, ...recorded.map((point) => point.value));
    const scale = Math.pow(10, Math.floor(Math.log10(max)));
    const step = Math.max(0.001, Math.ceil(max / scale / 4) * scale);
    const ceiling = Math.ceil(max / step) * step;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "Consommation par période en kWh");
    svg.style.cssText = "width:100%;height:auto;display:block";
    const make = (tag, attrs, text) => {
      const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
      if (text !== undefined) el.textContent = text;
      svg.appendChild(el);
      return el;
    };
    const format = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
    for (let tick = 0; tick <= 4; tick++) {
      const value = ceiling * tick / 4;
      const y = top + plotHeight * (1 - tick / 4);
      make("line", { x1: left, y1: y, x2: width - right, y2: y,
        stroke: "var(--divider-color)", "stroke-width": 1 });
      make("text", { x: left - 8, y: y + 4, "text-anchor": "end",
        fill: "var(--secondary-text-color)", "font-size": 11 }, format.format(value));
    }
    make("text", { x: 4, y: 12, fill: "var(--secondary-text-color)", "font-size": 11 }, "kWh");
    const slot = (width - left - right) / points.length;
    const formatter = new Intl.DateTimeFormat(locale,
      this._period === "day" ? { hour: "2-digit", minute: "2-digit" } :
        this._period === "year" ? { month: "short" } : { day: "2-digit", month: "2-digit" });
    const fullDate = new Intl.DateTimeFormat(locale, {
      weekday: "short", day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
    const tooltip = this._element("div", undefined,
      "display:none;position:absolute;z-index:2;pointer-events:none;background:var(--card-background-color);color:var(--primary-text-color);border:1px solid var(--divider-color);border-radius:8px;padding:8px 12px;box-shadow:0 2px 12px #0005;font-size:13px;max-width:240px");
    points.forEach((point, index) => {
      const x = left + index * slot;
      const date = new Date(point.time);
      if (point.value !== null) {
        const barHeight = plotHeight * point.value / ceiling;
        const bar = make("rect", { x: x + 2, y: top + plotHeight - barHeight,
          width: Math.max(1, slot - 4), height: barHeight,
          fill: this._period === "day" && this._hourTariff(point.time) === "HP" ? "#4f86f7" :
            this._period === "day" && this._hourTariff(point.time) === "HC" ? "#28558b" :
              "var(--primary-color)", rx: 2, tabindex: 0 });
        const tariff = this._period === "day" ? this._hourTariff(point.time) : null;
        const info = fullDate.format(date) + " : " + format.format(point.value) + " kWh" +
          (tariff ? " · " + tariff : "");
        bar.setAttribute("aria-label", info);
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = info;
        bar.appendChild(title);
        const show = () => {
          tooltip.textContent = info;
          tooltip.style.display = "block";
          tooltip.style.left = Math.min(75, Math.max(5, 100 * (x + slot / 2) / width)) + "%";
          tooltip.style.bottom = "25px";
        };
        const hide = () => { tooltip.style.display = "none"; };
        bar.addEventListener("mouseenter", show);
        bar.addEventListener("mouseleave", hide);
        bar.addEventListener("focus", show);
        bar.addEventListener("blur", hide);
        bar.addEventListener("click", () => {
          if (tooltip.style.display === "block") hide(); else show();
        });
      }
      const labelEvery = this._period === "year" ? 1 : Math.max(1, Math.ceil(points.length / 10));
      if (index % labelEvery === 0 || index === points.length - 1) {
        make("text", { x: x + slot / 2, y: height - 23,
          "text-anchor": "middle", fill: "var(--secondary-text-color)",
          "font-size": 11 }, formatter.format(date));
      }
    });
    if (this._period === "day" && this._tariffHistory?.length) {
      const legend = this._element("div", "■ HP (bleu clair)    ■ HC (bleu foncé)    ■ Indéterminé (couleur par défaut)",
        "font-size:12px;color:var(--secondary-text-color);padding:6px 0");
      box.appendChild(legend);
    }
    box.appendChild(svg);
    box.appendChild(tooltip);
    box.appendChild(this._element("div",
      "Consommation par " + (this._period === "day" ? "heure" :
        this._period === "year" ? "mois" : "jour") + " · " + recorded.length + " périodes",
      "font-size:12px;color:var(--secondary-text-color);text-align:right"));
    return box;
  }

  _render() {
    if (!this._config) return;
    if (!this._card) {
      this._card = document.createElement("ha-card");
      this.appendChild(this._card);
    }
    const openSections = new Set();
    for (const child of this._card.children[0]?.children || []) {
      if (child.tagName === "DETAILS" && child.open) openSections.add(child.children[0]?.textContent);
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

    const circuits = this._circuits();
    if (Array.isArray(circuits) && circuits.length) {
      const details = this._element("details", undefined, "margin-top:16px");
      details.open = openSections.has("Circuits");
      details.appendChild(this._element("summary", "Circuits",
        "cursor:pointer;font-weight:600;padding:8px 0"));
      for (const circuit of circuits) {
        if (!circuit || !circuit.entity) continue;
        const tile = this._element("div", undefined,
          "padding:14px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color,var(--card-background-color))");
        tile.appendChild(this._element("strong", circuit.name || circuit.entity));
        tile.appendChild(this._element("div", "Énergie aujourd’hui : " + this._value(circuit.entity, 3),
          "margin-top:8px"));
        if (circuit.power_entity) tile.appendChild(this._element("div",
          "Puissance moyenne : " + this._value(circuit.power_entity, 0), "margin-top:4px"));
        details.appendChild(tile);
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
      details.open = openSections.has("Contrat et diagnostics");
      details.appendChild(this._element("summary", "Contrat et diagnostics",
        "cursor:pointer;font-weight:600;padding:8px 0"));
      const grid = this._element("div", undefined,
        "display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));gap:12px;margin-top:12px");
      for (const [label, id] of diagnostics) {
        const tile = this._element("div", undefined,
          "padding:14px;border:1px solid var(--divider-color);border-radius:12px;background:var(--secondary-background-color,var(--card-background-color))");
        tile.appendChild(this._element("div", label,
          "font-size:12px;color:var(--secondary-text-color);margin-bottom:8px"));
        tile.appendChild(this._element("strong", label === "Prochain changement" ? (this._nextTariffChange() || "—") : this._value(id, label.startsWith("Prix ") ? 4 : 2),
          "font-size:16px;overflow-wrap:anywhere"));
        grid.appendChild(tile);
      }
      details.appendChild(grid);
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
