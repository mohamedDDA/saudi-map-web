/* Service worker: offline app shell + cached map tiles */
var APP = 'ksa-app-v2', TILES = 'ksa-tiles-v1';
var LF = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/';
var SHELL = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png',
  LF + 'leaflet.js', LF + 'leaflet.css', LF + 'images/layers.png', LF + 'images/layers-2x.png'];
function tkey(u) { return u.replace(/\/\/[abc]\.tile\.openstreetmap\.fr/, '//a.tile.openstreetmap.fr'); }
function isTile(u) { return /tile\.openstreetmap\.(org|fr)|World_Imagery\/MapServer\/tile/.test(u); }

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(APP).then(function (c) {
    return Promise.all(SHELL.map(function (u) {
      return fetch(u, { mode: /^http/.test(u) ? 'cors' : 'same-origin' })
        .then(function (r) { return r.ok ? c.put(u, r) : 0; }).catch(function () { return 0; });
    }));
  }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== APP && k !== TILES; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var r = e.request, u = r.url;
  if (r.method !== 'GET') return;
  if (/\/data\//.test(u)) return; // offline data is stored by the page itself
  if (/nominatim\.openstreetmap\.org|routing\.openstreetmap\.de/.test(u)) return; // live data only
  if (isTile(u)) { // cache-first tiles (CORS fetch keeps cached copies small)
    e.respondWith(caches.open(TILES).then(function (c) {
      return c.match(tkey(u)).then(function (hit) {
        return hit || fetch(u, { mode: 'cors' }).then(function (res) { if (res.ok) c.put(tkey(u), res.clone()); return res; });
      });
    }));
    return;
  }
  if (r.mode === 'navigate') { // network first, offline fallback to cached page
    e.respondWith(fetch(r).then(function (res) { var cp = res.clone(); caches.open(APP).then(function (c) { c.put('./index.html', cp); }); return res; })
      .catch(function () { return caches.match('./index.html'); }));
    return;
  }
  e.respondWith(caches.match(r).then(function (hit) {
    return hit || fetch(r).then(function (res) {
      if (res && (res.ok || res.type === 'opaque')) { var cp = res.clone(); caches.open(APP).then(function (c) { c.put(r, cp); }); }
      return res;
    });
  }));
});
