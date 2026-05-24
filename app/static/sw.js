// Couple Diary — minimal M1 service worker.
// Strategy:
//   - Static assets (CSS, JS, manifest, icons): cache-first.
//   - Everything else: network-first, fall back to cached HTML shell on offline.
// Refined offline behavior comes in M2 (PWA push notifications).
const CACHE_NAME = 'couple-diary-v1';
const STATIC_ASSETS = [
  '/static/css/theme.css',
  '/static/js/app.js',
  '/static/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;  // never cache POSTs
  const url = new URL(request.url);

  // Static assets — cache-first.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((resp) => {
        const copy = resp.clone();
        caches.open(CACHE_NAME).then((c) => c.put(request, copy));
        return resp;
      })),
    );
    return;
  }

  // Pages: network-first, fall back to any cached HTML on offline.
  event.respondWith(
    fetch(request)
      .then((resp) => {
        if (resp.ok && resp.headers.get('content-type', '').includes('text/html')) {
          const copy = resp.clone();
          caches.open(CACHE_NAME).then((c) => c.put(request, copy));
        }
        return resp;
      })
      .catch(() => caches.match(request)),
  );
});

self.addEventListener('push', (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (err) {
      data = { body: event.data.text() };
    }
  }

  const title = data.title || 'Couple Diary';
  const options = {
    body: data.body || '你有新的提醒',
    icon: data.icon || '/static/icons/icon-192.png',
    badge: data.badge || '/static/icons/icon-192.png',
    data: {
      url: data.url || '/',
    },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return self.clients.openWindow(url);
    }),
  );
});
