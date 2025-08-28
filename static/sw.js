const CACHE_NAME = "rosca-app-v5"; // ⚠️ aumente a versão sempre que atualizar
const urlsToCache = [
  "/",
  "/static/index.html",
  "/static/exemplo_roscas.png",
  "/static/fototeste.png",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/static/manifest.json"
];

// Instalação do Service Worker (pré-cache dos arquivos)
self.addEventListener("install", event => {
  console.log("[SW] Instalando...");
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log("[SW] Cache aberto:", CACHE_NAME);
      return cache.addAll(urlsToCache);
    })
  );
  self.skipWaiting(); // força ativação imediata
});

// Ativação e remoção de caches antigos
self.addEventListener("activate", event => {
  console.log("[SW] Ativando e limpando caches antigos...");
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log("[SW] Deletando cache antigo:", cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim(); // assume controle das abas abertas
});

// Estratégia de cache: Offline First
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    caches.match(event.request).then(response => {
      if (response) {
        console.log("[SW] Recurso carregado do cache:", event.request.url);
        return response;
      }
      console.log("[SW] Recurso não está no cache, buscando na rede:", event.request.url);

      return fetch(event.request).then(fetchResponse => {
        return caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, fetchResponse.clone());
          return fetchResponse;
        });
      }).catch(() => {
        console.warn("[SW] Offline! Retornando fallback para:", event.request.url);

        if (event.request.destination === "document") {
          return caches.match("/static/index.html");
        }
        if (event.request.destination === "image") {
          return caches.match("/static/offline.png") || caches.match("/static/icon-192.png");
        }
        if (event.request.destination === "style" || event.request.destination === "script") {
          return new Response("", { headers: { "Content-Type": "text/plain" } });
        }
      });
    })
  );
});
