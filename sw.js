// Service worker Top 30 Berita Saham.
// Tampilan aplikasi disimpan untuk dibuka offline; data selalu dicoba ambil terbaru dulu.
const SHELL = "top30-shell-v3";
const DATA = "top30-data-v3";
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

  // Data: jaringan dulu, cadangan dari cache saat offline. Kunci cache tanpa ?t= agar tidak menumpuk.
  if (url.pathname.includes("/data/")) {
    const key = url.origin + url.pathname;
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          if (res.ok) { const copy = res.clone(); caches.open(DATA).then((c) => c.put(key, copy)); }
          return res;
        })
        .catch(() => caches.match(key))
    );
    return;
  }

  // Tampilan aplikasi: jaringan dulu supaya versi baru langsung terpakai, cache saat offline.
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(SHELL).then((c) => c.put(event.request, copy)); }
        return res;
      })
      .catch(() => caches.match(event.request).then((hit) => hit || caches.match("./index.html")))
  );
});
