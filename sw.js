/* 승정 ERP 서비스워커 — 설치 가능 + 껍데기 오프라인 캐시 (항상 최신: 네트워크 우선) */
var CACHE = 'sj-erp-shell-v1';
var SHELL = ['index.html', 'index.html', 'sj-icon.png', 'manifest-erp.json', '로고/승정로고_투명.svg'];

self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL).catch(function () {}); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.map(function (k) { if (k !== CACHE) return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(function (r) {
      try { var cp = r.clone(); caches.open(CACHE).then(function (c) { c.put(e.request, cp); }); } catch (x) {}
      return r;
    }).catch(function () { return caches.match(e.request); })
  );
});
