// 聚合天气 Service Worker
// 策略：
//   - HTML 页面（./ 和 ./index.html）→ 网络优先（保证用户总能拿到最新 UI），失败时降级到缓存
//   - 其他静态资源（CSS/JS/图标/manifest/data.json）→ 缓存优先 + 后台更新
//   - /api/* 请求 → 网络优先（保证天气数据实时），失败时返回离线提示
const CACHE = 'weather-app-v2';
const SHELL = [
  './manifest.webmanifest',
  './data.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-512-maskable.png',
  './icons/icon-180.png',
  './icons/icon.svg',
  './icons/favicon-32.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);
  // 只处理同源 GET 请求
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;

  // API 请求：网络优先，失败降级
  if (url.pathname.indexOf('/api/') === 0) {
    e.respondWith(
      fetch(req).catch(() => new Response(
        JSON.stringify({ error: 'offline', message: '网络不可用，请检查连接后重试' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // HTML 页面（./ 和 ./index.html）：网络优先，确保用户拿到最新 UI 代码
  // 失败时（离线）才降级用缓存
  if (url.pathname === '/' || url.pathname === '/index.html' || url.pathname.endsWith('.html')) {
    e.respondWith(
      fetch(req).then((res) => {
        if (res && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone)).catch(() => {});
        }
        return res;
      }).catch(() => caches.match(req).then((cached) => cached || new Response('离线模式，请连接网络后刷新', { status: 503 })))
    );
    return;
  }

  // 其他静态资源：缓存优先 + 后台更新（stale-while-revalidate）
  e.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone)).catch(() => {});
        }
        return res;
      }).catch(() => cached);
      return cached || network;
    })
  );
});
