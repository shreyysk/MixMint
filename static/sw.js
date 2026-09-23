// MixMint service worker — static assets only, NEVER pages or API.
//
// Rules:
// - Navigation / HTML / API requests: network-only (always fresh deploys).
// - Versioned static files (css/js/img/fonts): stale-while-revalidate.
// - Old caches (mixmint-v1 etc.) are wiped on activate so a stuck SW
//   can never freeze the site on an old copy again.
const STATIC_CACHE = "mixmint-static-v2";

self.addEventListener("install", (event) => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) =>
                Promise.all(
                    keys
                        .filter((k) => k !== STATIC_CACHE)
                        .map((k) => caches.delete(k))
                )
            )
            .then(() => self.clients.claim())
    );
});

function isStaticAsset(url) {
    return (
        url.pathname.startsWith("/static/") &&
        /\.(css|js|png|jpg|jpeg|webp|svg|ico|woff2?|json)$/i.test(url.pathname)
    );
}

self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    // Only handle same-origin GET static assets; everything else goes to network.
    if (event.request.method !== "GET" || url.origin !== self.location.origin || !isStaticAsset(url)) {
        return;
    }
    event.respondWith(
        caches.open(STATIC_CACHE).then((cache) =>
            cache.match(event.request).then((cached) => {
                const network = fetch(event.request).then((response) => {
                    if (response && response.ok) {
                        cache.put(event.request, response.clone());
                    }
                    return response;
                });
                return cached || network;
            })
        )
    );
});
