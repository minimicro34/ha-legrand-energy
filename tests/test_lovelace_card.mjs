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
}

function createCard() {
  const registry = new Map();
  const window = {};
  runInNewContext(source, {
    HTMLElement: Element,
    document: { createElement: () => new Element() },
    customElements: {
      define: (name, constructor) => registry.set(name, constructor),
      get: (name) => registry.get(name),
    },
    window,
  });
  return { card: new (registry.get("legrand-energy-card"))(), window };
}

function values(card) {
  return card.children[0].children[0].children
    .slice(1)
    .map((row) => row.children[1].textContent);
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
  assert.deepEqual(values(card), ["3.4 kWh", "420 W"]);
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
