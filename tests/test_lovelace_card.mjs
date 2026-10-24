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
  assert.equal(card.getGridOptions().columns, 12);
});

test("reads compact Home Assistant history values and timestamps", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy" });
  let request;
  card.hass = {
    states: { "sensor.energy": { state: "3.4" } },
    callWS: async (payload) => {
      request = payload;
      return [[
        { s: "1.5", lu: Date.now() / 1000 - 120 },
        { s: "3.4", lu: Date.now() / 1000 },
      ]];
    },
  };
  await card._loadHistory();
  assert.equal(request.type, "history/history_during_period");
  assert.equal(request.entity_ids[0], "sensor.energy");
  assert.equal(card._history.length, 2);
  const chart = card._chart();
  assert.equal(chart.children[0].children[0].points.split(" ").length, 2);
});

test("distinguishes history request failure from missing measurements", async () => {
  const { card } = createCard();
  card.setConfig({ entity: "sensor.energy" });
  card.hass = {
    states: {},
    callWS: async () => { throw new Error("Recorder unavailable"); },
  };
  await card._loadHistory();
  assert.equal(card._historyError, true);
  assert.match(card._chart().children[0].textContent, /requête Home Assistant en échec/);
});
