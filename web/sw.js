const CACHE = 'olgal-comms-v1';
const ASSETS = ['./', 'assets/styles.css', 'assets/app.js', 'assets/manifest.webmanifest'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.method === 'GET' && !event.request.url.includes('/api/')) {
    event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request)));
  }
});
