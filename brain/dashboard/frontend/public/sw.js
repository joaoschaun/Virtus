/// <reference lib="webworker" />

const CACHE_NAME = 'virtus-cache-v1'
const STATIC_CACHE = 'virtus-static-v1'
const API_CACHE = 'virtus-api-v1'

// URLs para cachear estaticamente
const STATIC_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
]

// APIs para cachear com estratégia stale-while-revalidate
const API_PATTERNS = [
  /\/api\/market/,
  /\/api\/health/,
  /\/api\/brapi/,
]

declare const self: ServiceWorkerGlobalScope

// Install - cachear assets estáticos
self.addEventListener('install', (event) => {
  console.log('[SW] Install')
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_URLS)
    })
  )
  self.skipWaiting()
})

// Activate - limpar caches antigos
self.addEventListener('activate', (event) => {
  console.log('[SW] Activate')
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => caches.delete(name))
      )
    })
  )
  self.clients.claim()
})

// Fetch - estratégias de cache
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Ignorar requests não-GET
  if (request.method !== 'GET') return

  // Ignorar extensões do Chrome
  if (url.protocol === 'chrome-extension:') return

  // API requests - Network first, fallback to cache
  if (API_PATTERNS.some((pattern) => pattern.test(url.pathname))) {
    event.respondWith(networkFirstStrategy(request))
    return
  }

  // Assets estáticos - Cache first
  if (request.destination === 'script' || 
      request.destination === 'style' || 
      request.destination === 'image' ||
      request.destination === 'font') {
    event.respondWith(cacheFirstStrategy(request))
    return
  }

  // HTML - Network first (sempre buscar versão mais recente)
  if (request.destination === 'document') {
    event.respondWith(networkFirstStrategy(request))
    return
  }

  // Default - stale while revalidate
  event.respondWith(staleWhileRevalidate(request))
})

// Estratégia: Cache First
async function cacheFirstStrategy(request: Request): Promise<Response> {
  const cachedResponse = await caches.match(request)
  if (cachedResponse) {
    return cachedResponse
  }

  try {
    const networkResponse = await fetch(request)
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE)
      cache.put(request, networkResponse.clone())
    }
    return networkResponse
  } catch {
    return new Response('Offline', { status: 503 })
  }
}

// Estratégia: Network First
async function networkFirstStrategy(request: Request): Promise<Response> {
  try {
    const networkResponse = await fetch(request)
    if (networkResponse.ok) {
      const cache = await caches.open(API_CACHE)
      cache.put(request, networkResponse.clone())
    }
    return networkResponse
  } catch {
    const cachedResponse = await caches.match(request)
    if (cachedResponse) {
      return cachedResponse
    }
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

// Estratégia: Stale While Revalidate
async function staleWhileRevalidate(request: Request): Promise<Response> {
  const cachedResponse = await caches.match(request)
  
  const fetchPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      caches.open(CACHE_NAME).then((cache) => {
        cache.put(request, networkResponse.clone())
      })
    }
    return networkResponse
  }).catch(() => {
    // Se falhar, retorna null para usar cache
    return null
  })

  // Se tiver cache, retorna imediatamente e atualiza em background
  if (cachedResponse) {
    fetchPromise // Trigger background update
    return cachedResponse
  }

  // Se não tiver cache, espera a rede
  const networkResponse = await fetchPromise
  if (networkResponse) {
    return networkResponse
  }

  return new Response('Offline', { status: 503 })
}

// Push Notifications
self.addEventListener('push', (event) => {
  if (!event.data) return

  const data = event.data.json()
  const options: NotificationOptions = {
    body: data.body || 'Nova notificação do VIRTUS',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/dashboard',
    },
    actions: [
      { action: 'open', title: 'Abrir' },
      { action: 'close', title: 'Fechar' },
    ],
  }

  event.waitUntil(
    self.registration.showNotification(data.title || 'VIRTUS', options)
  )
})

// Notification click
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  if (event.action === 'close') return

  const url = event.notification.data?.url || '/dashboard'
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clientList) => {
      // Se já tem uma janela aberta, foca nela
      for (const client of clientList) {
        if ('focus' in client) {
          client.navigate(url)
          return client.focus()
        }
      }
      // Se não, abre uma nova
      if (self.clients.openWindow) {
        return self.clients.openWindow(url)
      }
    })
  )
})

// Background Sync
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-data') {
    event.waitUntil(syncData())
  }
})

async function syncData() {
  // Aqui você pode implementar sincronização de dados offline
  console.log('[SW] Syncing data...')
}

export {}
