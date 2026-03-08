const CACHE_NAME = 'mixmint-v1';
const ASSETS = [
    '/',
    '/static/css/style.css', // Assuming standard css path if exists later
    '/static/img/icon-512.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(ASSETS);
        })
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});
