// Service worker Top 30 Berita Saham.
// Tampilan aplikasi disimpan untuk dibuka offline; data edisi selalu dicoba ambil terbaru dulu.
const SHELL = "top30-shell-v2";
const DATA = "top30-data-v2";
const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;

  // Data edisi: jaringan dulu, cadangan dari cache saat offline.
  if (url.pathname.includes("/data/")) {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(DATA).then((c) => c.put(event.request, copy));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Tampilan aplikasi: cache dulu, lalu jaringan.
  event.respondWith(caches.match(event.request).then((hit) => hit || fetch(event.request)));
});
