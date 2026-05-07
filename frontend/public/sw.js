// Service worker for Helping Hands PWA.
// Caches the app shell on install; serves cached assets offline with a
// network-first strategy for navigations and cache-first for static assets.

const CACHE_NAME = "hh-shell-v1";

const APP_SHELL = [
  "/",
  "/offline.html",
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

// Install — pre-cache the app shell.
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// Activate — remove old caches.
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — network-first for navigations, cache-first for static assets.
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Skip non-GET and cross-origin requests.
  if (request.method !== "GET" || !request.url.startsWith(self.location.origin)) {
    return;
  }

  // Skip API/WebSocket routes — these should always hit the network.
  const url = new URL(request.url);
  const apiPrefixes = [
    "/build", "/tasks", "/monitor", "/health", "/version",
    "/workers", "/config", "/schedules", "/templates",
    "/grill", "/mgrill", "/arcade", "/repos", "/ws",
  ];
  if (apiPrefixes.some((p) => url.pathname.startsWith(p))) {
    return;
  }

  // Navigation requests: network-first, fall back to cache, then offline page.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return response;
        })
        .catch(() =>
          caches.match(request).then(
            (cached) => cached || caches.match("/offline.html")
          )
        )
    );
    return;
  }

  // Static assets: cache-first, fall back to network and cache the response.
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ||
        fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
    )
  );
});
