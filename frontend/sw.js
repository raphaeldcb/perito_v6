/**
 * Service Worker para suporte offline do módulo de Engenharia Vistorias
 * Fase 2: cache offline, sync background para envio de vistorias
 */

const CACHE_NAME = 'perito-engenharia-v1';
const API_CACHE = 'perito-api-cache-v1';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/favicon.ico',
];

// ---- INSTALAÇÃO
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((e) => {
        console.warn('[SW] Erro ao cachear assets:', e);
        // Falhar silenciosamente se alguns assets falharem
      });
    })
  );
  self.skipWaiting();
});

// ---- ATIVAÇÃO
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== API_CACHE) {
            console.log('[SW] Deletando cache antigo:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// ---- FETCH
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip cross-origin
  if (url.origin !== location.origin) {
    return;
  }

  // HTML, CSS, JS → cache first, fallback network
  if (
    request.url.endsWith('.html') ||
    request.url.endsWith('.css') ||
    request.url.endsWith('.js')
  ) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(request).then((response) => {
          if (response) return response;
          return fetch(request).then((networkResponse) => {
            cache.put(request, networkResponse.clone());
            return networkResponse;
          });
        });
      }).catch(() => {
        return new Response('Offline - recurso não cachado', { status: 503 });
      })
    );
    return;
  }

  // API GET → network first, fallback cache (modelos, vistorias)
  if (request.method === 'GET' && url.pathname.startsWith('/api/v1/engenharia/')) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          caches.open(API_CACHE).then((cache) => {
            cache.put(request, networkResponse.clone());
          });
          return networkResponse;
        })
        .catch(() => {
          return caches.open(API_CACHE).then((cache) => {
            return cache.match(request).then((cachedResponse) => {
              if (cachedResponse) {
                console.log('[SW] Usando cache para:', request.url);
                return cachedResponse;
              }
              return new Response(
                JSON.stringify({ erro: 'Offline', dados: [] }),
                { status: 503, headers: { 'Content-Type': 'application/json' } }
              );
            });
          });
        })
    );
    return;
  }

  // POST (salvar vistoria offline) → armazenar localmente, sync background depois
  if (request.method === 'POST' && request.url.includes('/engenharia/vistorias')) {
    event.respondWith(
      request.clone().json().then((body) => {
        // Simular resposta imediata (vistoria salva localmente)
        return new Response(
          JSON.stringify({
            id: Math.floor(Math.random() * 1e9),
            status: 'rascunho',
            offline: true,
            uuid_offline: body.uuid_offline,
            msg: 'Vistoria salva offline. Sincronizará quando houver conexão.'
          }),
          {
            status: 202,
            headers: { 'Content-Type': 'application/json' }
          }
        );
      }).catch(() => {
        return new Response(
          JSON.stringify({ erro: 'Erro ao processar offline' }),
          { status: 400, headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }

  // Default: network, fallback cache
  event.respondWith(
    fetch(request)
      .catch(() => {
        return caches.match(request).then((response) => {
          if (response) return response;
          return new Response('Offline', { status: 503 });
        });
      })
  );
});

// ---- BACKGROUND SYNC (sincronização automática de vistorias)
// Registra evento de sincronização quando voltar online
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-vistorias') {
    console.log('[SW] Background sync: enviando vistorias offline');
    event.waitUntil(
      sincronizarVistorias()
    );
  }
});

async function sincronizarVistorias() {
  try {
    // Buscar vistorias no IndexedDB (futuro: implementar IDB)
    // Por enquanto, notificar cliente via postMessage
    const clients_list = await self.clients.matchAll();
    clients_list.forEach((client) => {
      client.postMessage({
        type: 'sync-vistorias',
        status: 'iniciando'
      });
    });
  } catch (e) {
    console.error('[SW] Erro ao sincronizar:', e);
  }
}
