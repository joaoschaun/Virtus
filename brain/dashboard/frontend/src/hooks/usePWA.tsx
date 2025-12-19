/**
 * Hook para gerenciar funcionalidades PWA
 */

import { useState, useEffect, useCallback } from 'react'

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

interface UsePWAReturn {
  isInstalled: boolean
  isInstallable: boolean
  isOnline: boolean
  isUpdateAvailable: boolean
  install: () => Promise<boolean>
  update: () => void
}

export function usePWA(): UsePWAReturn {
  const [isInstalled, setIsInstalled] = useState(false)
  const [isInstallable, setIsInstallable] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [isUpdateAvailable, setIsUpdateAvailable] = useState(false)
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null)
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null)

  // Detectar se já está instalado
  useEffect(() => {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    const isIOSStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true
    setIsInstalled(isStandalone || isIOSStandalone)
  }, [])

  // Registrar Service Worker
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').then((reg) => {
        setRegistration(reg)
        
        // Verificar atualizações
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setIsUpdateAvailable(true)
              }
            })
          }
        })
      }).catch((error) => {
        console.error('[PWA] Service Worker registration failed:', error)
      })
    }
  }, [])

  // Listener para beforeinstallprompt
  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e as BeforeInstallPromptEvent)
      setIsInstallable(true)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    }
  }, [])

  // Listener para appinstalled
  useEffect(() => {
    const handleAppInstalled = () => {
      setIsInstalled(true)
      setIsInstallable(false)
      setDeferredPrompt(null)
    }

    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('appinstalled', handleAppInstalled)
    }
  }, [])

  // Listener para status online/offline
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Função para instalar PWA
  const install = useCallback(async (): Promise<boolean> => {
    if (!deferredPrompt) {
      console.warn('[PWA] Install prompt not available')
      return false
    }

    try {
      await deferredPrompt.prompt()
      const { outcome } = await deferredPrompt.userChoice
      
      if (outcome === 'accepted') {
        setIsInstalled(true)
        setIsInstallable(false)
      }
      
      setDeferredPrompt(null)
      return outcome === 'accepted'
    } catch (error) {
      console.error('[PWA] Install failed:', error)
      return false
    }
  }, [deferredPrompt])

  // Função para atualizar PWA
  const update = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      window.location.reload()
    }
  }, [registration])

  return {
    isInstalled,
    isInstallable,
    isOnline,
    isUpdateAvailable,
    install,
    update,
  }
}

// Componente de indicador de status online
export function OnlineStatus() {
  const { isOnline } = usePWA()

  if (isOnline) return null

  return (
    <div className="fixed bottom-4 left-4 z-50 bg-amber-500 text-black px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3" />
      </svg>
      <span className="font-medium">Offline - Alguns recursos podem estar indisponíveis</span>
    </div>
  )
}

// Componente de botão de instalação
export function InstallButton() {
  const { isInstallable, install, isInstalled } = usePWA()

  if (isInstalled || !isInstallable) return null

  return (
    <button
      onClick={install}
      className="flex items-center gap-2 px-4 py-2 bg-virtus-primary hover:bg-virtus-primary/80 text-white rounded-lg transition-colors"
    >
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      <span>Instalar App</span>
    </button>
  )
}

// Componente de atualização disponível
export function UpdatePrompt() {
  const { isUpdateAvailable, update } = usePWA()

  if (!isUpdateAvailable) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 bg-virtus-primary text-white px-4 py-3 rounded-lg shadow-lg">
      <p className="font-medium mb-2">Nova versão disponível!</p>
      <button
        onClick={update}
        className="bg-white text-virtus-primary px-3 py-1 rounded font-medium hover:bg-gray-100 transition-colors"
      >
        Atualizar agora
      </button>
    </div>
  )
}
