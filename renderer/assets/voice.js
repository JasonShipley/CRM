/* MCE quote assistant — the voice half that runs in the browser.
 *
 * Pressing the mic asks our server for a short-lived ElevenLabs conversation
 * (/api/voice/session — the API key never reaches this page), then talks to the
 * agent directly over WebRTC for the lowest delay. The agent answers equipment
 * questions only by calling the client tools below, and every one of them calls
 * this app's own /api/voice/* endpoints with the person's session — so a dealer's
 * assistant sees exactly what that dealer may see, and no number is spoken that
 * MCE's calculators did not produce.
 *
 * Plain ES2020 module, no build step. The ElevenLabs client is vendored in
 * assets/vendor/ and imported only on the first press.
 */
"use strict";

// a module script has no document.currentScript; find ours by its data
const SCRIPT = document.querySelector("script[data-session][data-client]");
const URLS = SCRIPT.dataset;
const $ = (id) => document.getElementById(id);
const btn = $("mce-voice-btn");
const panel = $("mce-voice");
const log = $("mce-voice-log");
const stateEl = $("mce-voice-state");

let conversation = null;
let starting = false;

function say(text, cls) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.textContent = text;
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
  return d;
}

function card(title, rows, link) {
  const d = document.createElement("div");
  d.className = "tool";
  const b = document.createElement("b");
  b.textContent = title;
  d.appendChild(b);
  if (rows && rows.length) {
    const ul = document.createElement("ul");
    rows.forEach((r) => {
      const li = document.createElement("li");
      li.textContent = r;
      ul.appendChild(li);
    });
    d.appendChild(ul);
  }
  if (link) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.text;
    d.appendChild(a);
  }
  log.appendChild(d);
  log.scrollTop = log.scrollHeight;
}

function setState(text, cls) {
  stateEl.textContent = text;
  stateEl.className = "state " + (cls || "");
}

async function api(url, opts) {
  const res = await fetch(url, Object.assign({
    credentials: "same-origin",
    headers: { "content-type": "application/json" },
  }, opts || {}));
  let data = {};
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok && !data.error) data.error = `The server answered ${res.status}.`;
  return data;
}

function asObject(v) {
  if (v && typeof v === "object") return v;
  if (typeof v === "string" && v.trim()) {
    try { return JSON.parse(v); } catch (e) { return {}; }
  }
  return {};
}

/* --------------------------------------------------------- client tools -- */
/* Each returns a short string for the voice model; the full answer goes on screen. */

const clientTools = {
  async list_equipment() {
    const data = await api(URLS.equipment);
    return JSON.stringify(data.equipment || data);
  },

  async explain_inputs(params) {
    const key = (params && params.equipment) || "";
    const data = await api(URLS.fields.replace("__KEY__", encodeURIComponent(key)));
    return JSON.stringify(data);
  },

  async size_equipment(params) {
    const key = (params && params.equipment) || "";
    const inputs = asObject(params && params.inputs);
    const data = await api(URLS.size.replace("__KEY__", encodeURIComponent(key)), {
      method: "POST", body: JSON.stringify({ inputs }),
    });
    const s = data.summary || {};
    if (data.error || s.error) {
      card("Could not size that", [data.error || s.error]);
    } else {
      card(s.equipment || "Sized", [...(s.results || []).slice(0, 6),
                                     ...(s.priced_lines || []),
                                     ...(s.total ? [`Total ${s.total}`] : [])]);
    }
    return JSON.stringify(s.error ? { error: s.error } : (data.error ? { error: data.error } : s));
  },

  async build_draft(params) {
    const job = asObject(params && params.job);
    const said = (params && params.said) || "";
    const data = await api(URLS.draft, {
      method: "POST", body: JSON.stringify({ job, said }),
    });
    if (data.error) {
      card("Could not build the draft", [data.error]);
      return JSON.stringify({ error: data.error });
    }
    const s = data.summary || {};
    if (window.MCE_FORM && typeof window.MCE_FORM.applyQuote === "function") {
      window.MCE_FORM.applyQuote(data.quote);
      card(`Draft on the form: ${s.quote || ""}`, s.lines || []);
      return JSON.stringify({ ...s, shown: "filled in on the quote form — review and save" });
    }
    try { sessionStorage.setItem("mce.voiceDraft", JSON.stringify(data.quote)); } catch (e) {}
    card(`Draft ready: ${s.quote || ""}`, s.lines || [],
         { href: URLS.newQuote + "?voice=1", text: "Open it as a new quote →" });
    return JSON.stringify({ ...s, shown: "ready to open as a new quote — tell them to tap the link" });
  },
};

/* ------------------------------------------------------------- session -- */

async function start() {
  if (conversation || starting) return;
  starting = true;
  setState("Connecting…");
  try {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
    } catch (e) {
      say("The microphone is blocked. Allow it for this site in the browser, then press the mic again.", "err");
      setState("No microphone");
      return;
    }
    const sess = await api(URLS.session, { method: "POST", body: "{}" });
    if (sess.error) {
      say(sess.error, "err");
      setState("Unavailable");
      return;
    }
    const { Conversation } = await import(URLS.client);
    const opts = {
      dynamicVariables: sess.dynamicVariables || {},
      clientTools,
      onConnect: () => {
        setState("Listening", "listening");
        btn.classList.add("live");
      },
      onDisconnect: () => {
        conversation = null;
        btn.classList.remove("live");
        setState("Ended");
      },
      onError: (message) => say(String(message || "Something went wrong."), "err"),
      onModeChange: ({ mode }) =>
        setState(mode === "speaking" ? "Speaking" : "Listening", mode),
      onMessage: ({ message, role, source }) => {
        if (!message) return;
        say(message, (role || source) === "user" ? "user" : "agent");
      },
    };
    if (sess.conversationToken) {
      opts.conversationToken = sess.conversationToken;
      opts.connectionType = "webrtc";
    } else {
      opts.signedUrl = sess.signedUrl;
      opts.connectionType = "websocket";
    }
    conversation = await Conversation.startSession(opts);
  } catch (e) {
    say("Could not start the conversation: " + (e && e.message ? e.message : e), "err");
    setState("Unavailable");
    conversation = null;
  } finally {
    starting = false;
  }
}

async function stop() {
  const c = conversation;
  conversation = null;
  btn.classList.remove("live");
  setState("Ended");
  if (c) {
    try { await c.endSession(); } catch (e) { /* already gone */ }
  }
}

btn.addEventListener("click", () => {
  if (panel.hidden) {
    panel.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    start();
  } else if (conversation) {
    stop();
  } else {
    start();
  }
});
$("mce-voice-end").addEventListener("click", async () => {
  await stop();
  panel.hidden = true;
  btn.setAttribute("aria-expanded", "false");
});
window.addEventListener("pagehide", () => { if (conversation) conversation.endSession(); });
