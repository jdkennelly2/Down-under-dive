// Offline shell for Deep Value ASX. Bump CACHE when you change the app.
const CACHE = "deep-value-asx-v2";
const CORE = [
  "./", "./index.html", "./data.json", "./manifest.webmanifest",
  "./apple-touch-icon.png", "./icon-192.png", "./icon-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      // Cache each item individually so one 404 can't fail the whole install.
      .then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const { request } = e;
  if (request.method !== "GET") return;

  // Network-first for the page itself and the data: an installed app must be
  // able to pick up a new build, and a fresh screener run must show through.
  // Cache-first here would pin the app to whatever copy it first cached.
  if (request.mode === "navigate" || /\.html$|data\.json$|manifest\.webmanifest$/.test(request.url)) {
    e.respondWith(
      fetch(request)
        .then(r => {
          caches.open(CACHE).then(c => c.put(request, r.clone()));
          return r;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Everything else (app shell, icons, fonts): cache first, then network.
  e.respondWith(
    caches.match(request).then(hit => hit || fetch(request).then(r => {
      if (r.ok && (request.url.startsWith(self.location.origin) || r.type === "cors")) {
        caches.open(CACHE).then(c => c.put(request, r.clone()));
      }
      return r;
    }).catch(() => hit))
  );
});
