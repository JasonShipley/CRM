// Minimal DOM shim: enough to run MCE's calculator scripts headless so their
// outputs can be diffed against the Python ports.
const fs = require("fs");

function makeEl(id) {
  const el = {
    id, _value: "", textContent: "", innerHTML: "", hidden: false, checked: false,
    disabled: false, style: {}, dataset: {}, options: [], tBodies: [], rows: [],
    classList: { _s: new Set(), add(...c){c.forEach(x=>this._s.add(x));},
      remove(...c){c.forEach(x=>this._s.delete(x));}, contains(c){return this._s.has(c);} },
    get value() { return this._value; },
    set value(v) { this._value = String(v); },
    setAttribute(){}, getAttribute(){return null;}, addEventListener(){},
    appendChild(c){ if (this.options !== undefined && c && c.__opt) this.options.push(c); return c; },
    insertRow(){ const r = makeEl(); this.rows.push(r); return r; },
    createTBody(){ const t = makeEl(); this.tBodies.push(t); return t; },
    querySelector(){ return makeEl(); }, querySelectorAll(){ return []; },
    get parentElement(){ return makeEl(); },
    get firstChild(){ return null; }, removeChild(){},
  };
  // tables are read as `table.tBodies[0].innerHTML = ...` by the calculators
  el.tBodies = [{ innerHTML: "", rows: [], insertRow() { const r = makeEl(); this.rows.push(r); return r; } }];
  return el;
}

function buildDocument(seed) {
  const els = new Map();
  const get = (id) => {
    if (!els.has(id)) { const e = makeEl(id); if (seed[id] !== undefined) e._value = String(seed[id]); els.set(id, e); }
    return els.get(id);
  };
  const document = {
    getElementById: get,
    querySelector: (s) => get("q:" + s),
    querySelectorAll: () => [],
    createElement: (tag) => { const e = makeEl(); if (tag === "option") e.__opt = true; return e; },
    body: makeEl("body"),
  };
  return { document, els, get };
}

function runCalc(htmlPath, seed, exportNames) {
  const html = fs.readFileSync(htmlPath, "utf8");
  // greedy to the LAST </script>: one calculator closes with </body></html>
  const m = html.match(/<script>([\s\S]*)<\/script>/);
  if (!m) throw new Error("no script block");
  const { document, get } = buildDocument(seed);
  const sandbox = { document, window: {}, console, Math, Number, String, Array, Object, JSON, parseInt, parseFloat, isNaN };
  sandbox.globalThis = sandbox;
  const vm = require("vm");
  vm.createContext(sandbox);
  const src = m[1] + "\n;globalThis.__exports = {" +
    exportNames.map(n => `${n}: typeof ${n} !== "undefined" ? ${n} : undefined`).join(",") + "};";
  vm.runInContext(src, sandbox, { filename: htmlPath });
  return { exports: sandbox.__exports, get, sandbox };
}

module.exports = { runCalc, makeEl };
