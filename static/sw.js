const CACHE_NAME = "rosca-app-v4"; // ⚠️ aumente a versão sempre que atualizar
const urlsToCache = [
  "/",
  "/static/index.html",
  "/static/exemplo_roscas.png",  // imagem exemplo
  "/static/fototeste.png",       // foto teste
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
  event.respondWith(
    caches.match(event.request).then(response => {
      if (response) {
        return response; // retorna do cache
      }
      // busca na rede e salva no cache
      return fetch(event.request).then(fetchResponse => {
        return caches.open(CACHE_NAME).then(cache => {
          if (event.request.method === "GET") {
            cache.put(event.request, fetchResponse.clone());
          }
          return fetchResponse;
        });
      }).catch(() => {
        // fallback se offline e recurso não estiver no cache
        if (event.request.destination === "document") {
          return caches.match("/static/index.html");
        }
        if (event.request.destination === "image") {
          return caches.match("/static/offline.png") || caches.match("/static/icon-192.png");
        }
      });
    })
  );
});
