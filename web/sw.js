const CACHE = 'olgal-hearth-v4';
const ASSETS = [
  './',
  'assets/styles.css?v=6',
  'assets/app.js?v=6',
  'assets/assets/hearth-background.webp',
  'assets/icons/gear-six.svg',
  'assets/icons/phone-call.svg',
  'assets/icons/clock.svg',
  'assets/icons/microphone.svg',
  'assets/icons/cassette-tape.svg',
  'assets/icons/chat-circle-dots.svg',
  'assets/icons/house-simple.svg',
  'assets/icons/envelope-simple.svg',
  'assets/icons/check-circle.svg',
  'assets/icons/x.svg',
  'assets/icons/trash.svg',
  'assets/icons/lock-key.svg',
  'assets/icons/caret-right.svg',
  'assets/icons/waveform.svg',
  'manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match('./')));
    return;
  }
  event.respondWith(caches.match(event.request).then((hit) => hit || fetch(event.request)));
});
