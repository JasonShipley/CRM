/* The MCE Quotes service worker. It does one thing: when a page can't load because
 * there is no connection, it shows a "No connection — try again" page instead of a
 * dead screen. A Home Screen app has no reload button of its own.
 *
 * It never caches a page, a quote, a price or an API answer. Every request goes to
 * the network exactly as it would without this file. Only the offline page and
 * what it draws with are kept. tests/test_app_install.py holds it to that.
 */
const CACHE = "mce-offline-v1";
const OFFLINE = [
  "/assets/offline.html",
  "/assets/mce-logo.png",
  "/assets/fonts/oswald.woff2",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(OFFLINE)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || req.mode !== "navigate") return;   // the network, untouched
  event.respondWith(
    fetch(req).catch(() => caches.match("/assets/offline.html")));
});
