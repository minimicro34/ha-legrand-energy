import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";

const source = readFileSync(
  new URL("../custom_components/legrand_energy/www/legrand-energy-card.js", import.meta.url),
  "utf8",
);

class Element {
  constructor() {
    this.children = [];
    this.style = {};
    this.textContent = "";
  }
  appendChild(child) { this.children.push(child); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  addEventListener(name, callback) { this["on_" + name] = callback; }
  setAttribute(name, value) { this[name] = value; }
}

function createCard() {
  const registry = new Map();
  const window = {};
  runInNewContext(source, {
    HTMLElement: Element,
    document: { createElement: () => new Element(), createElementNS: () => new Element() },
    Intl, Date, Number, Array, Math,
    customElements: {
      define: (name, constructor) => registry.set(name, constructor),
      get: (name) => registry.get(name),
    },
    window,
  });
  return { card: new (registry.get("legrand-energy-card"))(), window };
}

function values(card) {
  return card.children[0].children[0].children[1].children
    .map((tile) => tile.children[1].textContent);
}

test("requires a configured energy entity", () => {
  const { card } = createCard();
  assert.throws(() => card.setConfig({}), /energy entity is required/);
  assert.throws(() => card.setConfig({ entity: " " }), /energy entity is required/);
});

test("renders configured readings and units", () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy", power_entity: "sensor.power" });
  card.hass = {
    states: {
      "sensor.energy": { state: "3.4", attributes: { unit_of_measurement: "kWh" } },
      "sensor.power": { state: "420", attributes: { unit_of_measurement: "W" } },
    },
  };
  assert.deepEqual(values(card), ["3,4 kWh", "420 W"]);
});

test("handles missing, unavailable, and incomplete entities", () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    power_entity: "sensor.power",
    cost_entity: "sensor.cost",
  });
  card.hass = {
    states: {
      "sensor.energy": { state: "unavailable", attributes: {} },
      "sensor.power": { state: "15" },
    },
  };
  assert.deepEqual(values(card), ["—", "15", "—"]);
});

test("registers Lovelace card and leaves entity selection to the user", () => {
  const { card, window } = createCard();
  assert.equal(window.customCards[0].type, "legrand-energy-card");
  assert.equal(card.constructor.getStubConfig().entity, "");
});

test("renders period tabs, circuits and collapsible diagnostics", () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    week_entity: "sensor.week",
    circuits: [{ name: "Chauffage", entity: "sensor.heating" }],
    subscribed_power_entity: "sensor.subscribed",
  });
  card.hass = { states: {
    "sensor.energy": { state: "2", attributes: { unit_of_measurement: "kWh" } },
    "sensor.week": { state: "12", attributes: { unit_of_measurement: "kWh" } },
    "sensor.heating": { state: "200", attributes: { unit_of_measurement: "W" } },
    "sensor.subscribed": { state: "6", attributes: { unit_of_measurement: "kVA" } },
  }};
  const wrapper = card.children[0].children[0];
  assert.equal(wrapper.children[2].children.length, 4);
  assert.equal(wrapper.children[5].children[0].textContent, "Circuits");
  assert.equal(wrapper.children[6].children[0].textContent, "Contrat et diagnostics");
  wrapper.children[2].children[1].on_click();
  assert.match(card.children[0].children[0].children[3].children[1].textContent, /12 kWh/);
});

test("auto-discovers period and contract sensors for the selected EcoMeter", () => {
  const { card } = createCard();
  const prefix = "sensor.house_legrand_ecometer_";
  card.setConfig({ entity: prefix + "consommation_aujourd_hui" });
  card.hass = { states: {
    [prefix + "consommation_aujourd_hui"]: { state: "3" },
    [prefix + "energie"]: { state: "12" },
    [prefix + "energie_2"]: { state: "40" },
    [prefix + "energie_3"]: { state: "500" },
    [prefix + "puissance_souscrite"]: { state: "6", attributes: { unit_of_measurement: "kVA" } },
    "sensor.other_legrand_ecometer_energie": { state: "999" },
  }};
  assert.equal(card._autoEntity(null, ["puissance_souscrite"]), prefix + "puissance_souscrite");
  assert.equal(card.children[0].children[0].children.at(-1).children[0].textContent, "Contrat et diagnostics");
  for (const [period, suffix] of [["week", "energie"], ["month", "energie_2"], ["year", "energie_3"]]) {
    card._period = period;
    assert.equal(card._periodEntity(), prefix + suffix);
  }
  assert.equal(card.getGridOptions().columns, 36);
});

test("reads Recorder statistics and computes period consumption", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy" });
  // Fixed interval avoids a midnight-dependent assertion when tests run just after 00:00.
  card._dateRange = () => ({
    start: new Date("2026-10-24T00:00:00Z"),
    end: new Date("2026-10-24T04:00:00Z"),
  });
  let request;
  card._hass = {
    states: { "sensor.energy": { state: "3.4" } },
    callWS: async (payload) => {
      if (payload.type === "config/entity_registry/list") return [];
      if (payload.period === "5minute") return { "sensor.energy": [] };
      request = payload;
      const beginning = new Date(payload.start_time).getTime();
      return { "sensor.energy": [
        { start: beginning, sum: 100 },
        { start: beginning + 3600000, sum: 101.5 },
        { start: beginning + 7200000, sum: 103.4 },
      ] };
    },
  };
  await card._loadHistory();
  assert.equal(request.type, "recorder/statistics_during_period");
  assert.equal(request.statistic_ids[0], "sensor.energy");
  assert.equal(card._history.length, 2);
  assert.ok(Math.abs(card._history[0].value - 1.5) < 0.001);
  assert.equal(new Date(card._history[0].time).getTime(), new Date(request.start_time).getTime() + 3600000);
  const chart = card._chart();
  assert.equal(chart.children[0].children.filter((element) => element.rx === 2).length, 2);
});

test("distinguishes history request failure from missing measurements", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy" });
  card._hass = {
    states: {},
    callWS: async () => { throw new Error("Recorder unavailable"); },
  };
  await card._loadHistory();
  assert.equal(card._historyError, true);
  assert.match(card._chart().children[0].textContent, /requête Home Assistant en échec/);
});

test("discovers renamed sensors by registry unique ID without mixing EcoMeters", () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.renamed_daily" });
  card.hass = {
    states: {
      "sensor.renamed_daily": { state: "2" },
      "sensor.renamed_week": { state: "15" },
      "sensor.other_week": { state: "999" },
    },
    entities: {
      "sensor.renamed_daily": {
        entity_id: "sensor.renamed_daily", platform: "legrand_energy",
        unique_id: "module_A_energy_today",
      },
      "sensor.renamed_week": {
        entity_id: "sensor.renamed_week", platform: "legrand_energy",
        unique_id: "module_A_energy_week",
      },
      "sensor.other_week": {
        entity_id: "sensor.other_week", platform: "legrand_energy",
        unique_id: "module_B_energy_week",
      },
    },
  };
  card._period = "week";
  assert.equal(card._periodEntity(), "sensor.renamed_week");
  assert.equal(card._autoEntity(null, ["energie_2"], "energy_month"), null);
  assert.equal(card._autoEntity("sensor.manual", ["energie"], "energy_week"), "sensor.manual");
});

test("auto-discovers only circuits attached to the selected EcoMeter", () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.main_energy" });
  card.hass = {
    states: {
      "sensor.main_energy": { state: "10" },
      "sensor.circuit_energy": { state: "2", attributes: { friendly_name: "Chauffage énergie" } },
      "sensor.circuit_power": { state: "350" },
      "sensor.other_circuit": { state: "99" },
    },
    entities: {
      "sensor.main_energy": { entity_id: "sensor.main_energy", platform: "legrand_energy", unique_id: "meterA_energy_today" },
      "sensor.circuit_energy": { entity_id: "sensor.circuit_energy", platform: "legrand_energy", unique_id: "meterA#0_circuit_energy_today" },
      "sensor.circuit_power": { entity_id: "sensor.circuit_power", platform: "legrand_energy", unique_id: "meterA#0_circuit_average_power" },
      "sensor.other_circuit": { entity_id: "sensor.other_circuit", platform: "legrand_energy", unique_id: "meterB#0_circuit_energy_today" },
    },
  };
  const circuits = card._circuits();
  assert.equal(circuits.length, 1);
  assert.equal(circuits[0].entity, "sensor.circuit_energy");
  assert.equal(circuits[0].power_entity, "sensor.circuit_power");
});

test("loads the entity registry and discovers circuits without hass.entities", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.main" });
  card.hass = {
    states: {
      "sensor.main": { state: "4" },
      "sensor.circuit": { state: "1" },
    },
    callWS: async ({ type }) => {
      if (type === "config/entity_registry/list") return [
        { entity_id: "sensor.main", platform: "legrand_energy", unique_id: "meter_energy_today" },
        { entity_id: "sensor.circuit", platform: "legrand_energy", unique_id: "meter#0_circuit_energy_today" },
      ];
      return {};
    },
  };
  await card._loadEntityRegistry();
  assert.equal(card._circuits().length, 1);
  assert.equal(card._circuits()[0].entity, "sensor.circuit");
});

test("aligns July and August monthly totals and HP/HC splits", async () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    peak_energy_entity: "sensor.hp",
    offpeak_energy_entity: "sensor.hc",
  });
  card._period = "year";
  card._dateRange = () => ({
    start: new Date("2026-01-01T00:00:00Z"),
    end: new Date("2026-10-25T12:00:00Z"),
  });
  const month = (value) => { const [year, mon] = value.slice(0, 7).split("-").map(Number); return new Date(year, mon - 1, 1).getTime(); };
  const starts = [
    "2026-06-01T00:00:00Z",
    "2026-07-01T00:00:00Z",
    "2026-08-01T00:00:00Z",
    "2026-09-01T00:00:00Z",
  ].map(month);
  const sums = {
    "sensor.energy": [100, 100, 115, 135],
    "sensor.hp": [60, 60, 70, 82],
    "sensor.hc": [40, 40, 45, 53],
  };
  const requests = [];
  card._hass = {
    states: {
      "sensor.energy": { state: "35" },
      "sensor.hp": { state: "20" },
      "sensor.hc": { state: "15" },
    },
    callWS: async (payload) => {
      if (payload.type === "config/entity_registry/list") return [];
      requests.push(payload);
      return Object.fromEntries(payload.statistic_ids.map((id) => [
        id, starts.map((start, index) => ({ start, sum: sums[id][index] })),
      ]));
    },
  };
  await card._loadHistory();
  // Registry discovery can trigger a second history load; only assert the
  // distinct Recorder request shapes, not their scheduling/count.
  assert.ok(requests.length >= 2);
  assert.ok(requests.some((request) => request.period === "month"));
  assert.ok(requests.some((request) => request.period === "day"));
  assert.ok(requests.some((request) => request.statistic_ids.includes("sensor.energy")));
  assert.ok(requests.some((request) => request.statistic_ids.includes("sensor.hp") && request.statistic_ids.includes("sensor.hc")));
  // July has a valid zero delta; August and September follow it.
  assert.equal(card._history.length, 3);
  assert.equal(new Date(card._history[0].time).getMonth(), 6);
  assert.equal(card._history[0].value, 0);
  assert.equal(new Date(card._history[1].time).getMonth(), 7);
  assert.equal(card._history[1].value, 15);
  assert.equal(new Date(card._history[2].time).getMonth(), 8);
  assert.equal(card._history[2].value, 20);
  assert.equal(card._splitHistory.peak.get(starts[2]), 10);
  assert.equal(card._splitHistory.offPeak.get(starts[2]), 5);
  assert.equal(card._splitHistory.peak.get(starts[3]), 12);
  assert.equal(card._splitHistory.offPeak.get(starts[3]), 8);
});

test("recovers the first recorded month from daily statistics without shifting later months", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy", peak_energy_entity: "sensor.hp",
    offpeak_energy_entity: "sensor.hc" });
  card._period = "year";
  card._dateRange = () => ({ start: new Date(2026, 0, 1),
    end: new Date(2026, 9, 25, 12) });
  const months = [6, 7, 8, 9].map((month) => new Date(2026, month, 1).getTime());
  const monthly = { "sensor.energy": [100, 115, 135, 150],
    "sensor.hp": [60, 70, 82, 90], "sensor.hc": [40, 45, 53, 60] };
  const dailyStarts = [new Date(2026, 5, 30), new Date(2026, 6, 1),
    new Date(2026, 6, 2), new Date(2026, 6, 3)].map((date) => date.getTime());
  const daily = { "sensor.energy": [90, 93, 97, 100],
    "sensor.hp": [54, 56, 58, 60], "sensor.hc": [36, 37, 39, 40] };
  card._hass = { states: {}, callWS: async (payload) => {
    if (payload.type === "config/entity_registry/list") return [];
    const isDaily = payload.period === "day";
    const starts = isDaily ? dailyStarts : months;
    const sums = isDaily ? daily : monthly;
    return Object.fromEntries(payload.statistic_ids.map((id) => [
      id, starts.map((start, index) => ({ start, sum: sums[id][index] })),
    ]));
  } };
  await card._loadHistory();
  const values = new Map(card._history.map((point) => [new Date(point.time).getMonth(), point.value]));
  assert.equal(values.get(6), 10);
  assert.equal(values.get(7), 15);
  assert.equal(values.get(8), 20);
  assert.equal(values.get(9), 15);
  assert.equal(card._splitHistory.peak.get(months[0]), 6);
  assert.equal(card._splitHistory.offPeak.get(months[0]), 4);
});

test("renders both autumn DST 02:00 buckets with distinct UTC offsets", () => {
  const previousTZ = process.env.TZ;
  try {
    process.env.TZ = "Europe/Paris";
    const { card } = createCard();
    card.setConfig({ entity: "sensor.energy" });
    card.hass = { states: { "sensor.energy": { state: "2" } } };
    card._period = "day";
    card._dateRange = () => ({
      start: new Date("2026-10-24T22:00:00Z"),
      end: new Date("2026-10-25T12:00:00Z"),
    });
    card._history = [
      { time: Date.parse("2026-10-25T00:00:00Z"), value: 1 },
      { time: Date.parse("2026-10-25T01:00:00Z"), value: 1 },
    ];
    const chart = card._chart();
    const svg = chart.children.find((child) => child.role === "img");
    // The x-axis intentionally skips labels on crowded 25-hour days.
    // Verify both 02:00 slots through the actual bars and their tooltips.
    const bars = svg.children.filter((child) => child.rx === 2 && child.tabindex === 0);
    assert.equal(bars.length, 2);
    assert.notEqual(bars[0].x, bars[1].x);
    assert.match(bars[0]["aria-label"], /02:00/);
    assert.match(bars[1]["aria-label"], /02:00/);
    assert.notEqual(bars[0]["aria-label"], bars[1]["aria-label"]);
  } finally {
    if (previousTZ === undefined) delete process.env.TZ;
    else process.env.TZ = previousTZ;
  }
});

test("aligns completed monthly buckets and skips daily fallback when October monthly data exists", async () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    peak_energy_entity: "sensor.hp",
    offpeak_energy_entity: "sensor.hc",
  });
  card._period = "year";
  card._dateRange = () => ({
    start: new Date("2026-01-01T00:00:00Z"),
    end: new Date("2026-10-25T12:00:00Z"),
  });
  const monthlyStarts = [
    "2026-07-01T00:00:00Z",
    "2026-08-01T00:00:00Z",
    "2026-09-01T00:00:00Z",
    "2026-10-01T00:00:00Z",
  ].map((value) => { const [year, mon] = value.slice(0, 7).split("-").map(Number); return new Date(year, mon - 1, 1).getTime(); });
  const monthly = {
    "sensor.energy": [100, 115, 135, 150],
    "sensor.hp": [60, 70, 82, 90],
    "sensor.hc": [40, 45, 53, 60],
  };
  const dailyStarts = [
    "2026-09-30T00:00:00Z",
    "2026-10-01T00:00:00Z",
    "2026-10-02T00:00:00Z",
    "2026-10-03T00:00:00Z",
  ].map(Date.parse);
  const daily = {
    "sensor.energy": [150, 152, 156, 160],
    "sensor.hp": [90, 91, 93, 95],
    "sensor.hc": [60, 61, 63, 65],
  };
  const requests = [];
  // Assign the mock directly: the hass setter starts an unawaited load.
  card._hass = {
    states: {
      "sensor.energy": { state: "160" },
      "sensor.hp": { state: "95" },
      "sensor.hc": { state: "65" },
    },
    callWS: async (payload) => {
      if (payload.type === "config/entity_registry/list") return [];
      requests.push(payload);
      const isDaily = payload.period === "day";
      const starts = isDaily ? dailyStarts : monthlyStarts;
      const sums = isDaily ? daily : monthly;
      return Object.fromEntries(payload.statistic_ids.map((id) => [
        id, starts.map((start, index) => ({ start, sum: sums[id][index] })),
      ]));
    },
  };
  await card._loadHistory();
  assert.ok(requests.some((request) => request.period === "day" &&
    request.statistic_ids.includes("sensor.energy") &&
    new Date(request.start_time).getMonth() === 5));
  assert.ok(!requests.some((request) => request.period === "day" &&
    new Date(request.start_time).getMonth() === 8));
  const byMonth = new Map(card._history.map((point) => [
    new Date(point.time).getMonth(), point.value,
  ]));
  assert.equal(byMonth.get(7), 15);
  assert.equal(byMonth.get(8), 20);
  assert.equal(byMonth.get(9), 15);
  assert.equal(byMonth.get(6), undefined);
  const october = new Date(2026, 9, 1).getTime();
  assert.equal(card._splitHistory.peak.get(october), 8);
  assert.equal(card._splitHistory.offPeak.get(october), 7);
});

test("groups five-minute energy and HP/HC deltas into half-hour day bars", async () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    peak_energy_entity: "sensor.hp",
    offpeak_energy_entity: "sensor.hc",
  });
  card._dateRange = () => ({
    start: new Date("2026-10-24T00:00:00Z"),
    end: new Date("2026-10-24T01:00:00Z"),
  });
  const starts = Array.from({ length: 13 }, (_, i) =>
    Date.parse("2026-10-23T23:55:00Z") + i * 300000);
  const cumulative = {
    "sensor.energy": starts.map((_, i) => 100 + i),
    "sensor.hp": starts.map((_, i) => 60 + i * 0.6),
    "sensor.hc": starts.map((_, i) => 40 + i * 0.4),
  };
  const requests = [];
  card._hass = {
    states: {
      "sensor.energy": { state: "12" },
      "sensor.hp": { state: "7.2" },
      "sensor.hc": { state: "4.8" },
    },
    callWS: async (payload) => {
      requests.push(payload);
      return Object.fromEntries(payload.statistic_ids.map((id) => [
        id, starts.map((start, i) => ({ start, sum: cumulative[id][i] })),
      ]));
    },
  };
  await card._loadHistory();
  assert.equal(card._dayGranularity, 1800000);
  assert.ok(requests.every((request) => request.period === "5minute"));
  assert.equal(card._history.length, 2);
  assert.equal(card._history[0].value, 6);
  assert.equal(card._history[1].value, 6);
  const first = Date.parse("2026-10-24T00:00:00Z");
  assert.ok(Math.abs(card._splitHistory.peak.get(first) - 3.6) < 1e-9);
  assert.ok(Math.abs(card._splitHistory.offPeak.get(first) - 2.4) < 1e-9);
  const svg = card._chart().children.find((child) => child.role === "img");
  const bars = svg.children.filter((child) => child.rx === 2 && child.tabindex === 0);
  assert.equal(bars.length, 2);
});

test("keeps half-hour bars when five-minute Recorder samples contain a gap", async () => {
  const { card } = createCard();
  card.setConfig({
    entity: "sensor.energy",
    peak_energy_entity: "sensor.hp",
    offpeak_energy_entity: "sensor.hc",
  });
  card._dateRange = () => ({
    start: new Date("2026-10-24T00:00:00Z"),
    end: new Date("2026-10-24T01:00:00Z"),
  });
  const starts = [
    Date.parse("2026-10-23T23:55:00Z"),
    Date.parse("2026-10-24T00:00:00Z"),
    Date.parse("2026-10-24T00:05:00Z"),
    Date.parse("2026-10-24T00:30:00Z"),
    Date.parse("2026-10-24T00:35:00Z"),
    Date.parse("2026-10-24T00:40:00Z"),
  ];
  const requests = [];
  card._hass = {
    states: {},
    callWS: async (request) => {
      requests.push(request);
      return Object.fromEntries(request.statistic_ids.map((id) => [
        id, starts.map((start, index) => ({
          start,
          sum: index === 3 ? 20 : index > 3 ? 20 + index - 3 : index,
        })),
      ]));
    },
  };
  await card._loadHistory();
  assert.equal(card._historyError, false);
  assert.equal(card._dayGranularity, 1800000);
  assert.ok(requests.every((request) => request.period === "5minute"));
  assert.deepEqual(Array.from(card._history, (point) => point.value), [2, 2]);
  const second = Date.parse("2026-10-24T00:30:00Z");
  assert.equal(card._splitHistory.peak.get(second), 2);
  assert.equal(card._splitHistory.offPeak.get(second), 2);
  assert.equal(card._unallocatedEnergy, 18);
  assert.equal(card._unallocatedGaps, 1);
  const chart = card._chart();
  const svg = chart.children.find((child) => child.role === "img");
  const bars = svg.children.filter((child) => child.rx === 2 && child.tabindex === 0);
  assert.equal(bars.length, 3);
  assert.match(bars[2].children[0].textContent, /Non répartie.*18.*kWh/);
  assert.ok(svg.children.some((child) => child.textContent === "N/R"));
  assert.match(chart.children.at(-1).textContent, /Hors créneaux.*18/);
});
