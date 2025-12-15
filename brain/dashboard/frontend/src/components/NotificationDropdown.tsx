import { useEffect, useRef } from 'react'
import { useNotificationStore, NotificationType, NotificationPriority } from '../stores/notificationStore'
import {
  Bell,
  X,
  Check,
  CheckCheck,
  Trash2,
  TrendingUp,
  AlertTriangle,
  Bot,
  Newspaper,
  Settings,
  RefreshCw,
} from 'lucide-react'
import { cn } from '../lib/utils'

// Ícones por tipo de notificação
const typeIcons: Record<NotificationType, typeof Bell> = {
  trade: TrendingUp,
  alert: AlertTriangle,
  bot: Bot,
  news: Newspaper,
  system: Settings,
}

// Cores por tipo
const typeColors: Record<NotificationType, string> = {
  trade: 'text-virtus-accent-success',
  alert: 'text-virtus-accent-warning',
  bot: 'text-virtus-accent-primary',
  news: 'text-virtus-accent-info',
  system: 'text-virtus-text-secondary',
}

// Cores de prioridade para o indicador
const priorityColors: Record<NotificationPriority, string> = {
  low: 'bg-virtus-text-muted',
  medium: 'bg-virtus-accent-warning',
  high: 'bg-virtus-accent-danger',
}

export default function NotificationDropdown() {
  const {
    notifications,
    unreadCount,
    isLoading,
    isOpen,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    clearAll,
    setOpen,
    toggleOpen,
  } = useNotificationStore()
  
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  // Fetch notifications on mount and periodically
  useEffect(() => {
    fetchNotifications()
    
    // Poll for new notifications every 30 seconds
    const interval = setInterval(() => {
      fetchUnreadCount()
    }, 30000)
    
    return () => clearInterval(interval)
  }, [fetchNotifications, fetchUnreadCount])
  
  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, setOpen])
  
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)
    
    if (minutes < 1) return 'Agora'
    if (minutes < 60) return `${minutes}m atrás`
    if (hours < 24) return `${hours}h atrás`
    if (days < 7) return `${days}d atrás`
    return date.toLocaleDateString('pt-BR')
  }
  
  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={toggleOpen}
        className="relative p-2 rounded-lg hover:bg-virtus-bg-hover transition-colors"
      >
        <Bell className={cn(
          'w-5 h-5 transition-colors',
          isOpen ? 'text-virtus-accent-primary' : 'text-virtus-text-secondary'
        )} />
        
        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center bg-virtus-accent-danger text-white text-[10px] font-bold rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      
      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-virtus-bg-card border border-virtus-border-primary rounded-xl shadow-virtus-lg z-50 animate-slideDown overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-virtus-border-primary">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-virtus-accent-primary" />
              <h3 className="font-semibold">Notificações</h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 bg-virtus-accent-primary/20 text-virtus-accent-primary text-xs rounded-full">
                  {unreadCount} novas
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="p-1.5 text-virtus-text-muted hover:text-virtus-accent-primary hover:bg-virtus-bg-hover rounded-lg transition-colors"
                  title="Marcar todas como lidas"
                >
                  <CheckCheck className="w-4 h-4" />
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={clearAll}
                  className="p-1.5 text-virtus-text-muted hover:text-virtus-accent-danger hover:bg-virtus-bg-hover rounded-lg transition-colors"
                  title="Limpar todas"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 text-virtus-text-muted hover:text-virtus-text-primary hover:bg-virtus-bg-hover rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Notifications List */}
          <div className="max-h-[400px] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-6 h-6 animate-spin text-virtus-accent-primary" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-virtus-text-muted">
                <Bell className="w-10 h-10 mb-2 opacity-50" />
                <p className="text-sm">Nenhuma notificação</p>
              </div>
            ) : (
              <div className="divide-y divide-virtus-border-primary">
                {notifications.map((notification) => {
                  const Icon = typeIcons[notification.type] || Bell
                  
                  return (
                    <div
                      key={notification.id}
                      className={cn(
                        'flex gap-3 p-3 hover:bg-virtus-bg-hover transition-colors cursor-pointer group',
                        !notification.read && 'bg-virtus-accent-primary/5'
                      )}
                      onClick={() => !notification.read && markAsRead(notification.id)}
                    >
                      {/* Icon */}
                      <div className={cn(
                        'flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center',
                        notification.read ? 'bg-virtus-bg-tertiary' : 'bg-virtus-accent-primary/10'
                      )}>
                        <Icon className={cn('w-4 h-4', typeColors[notification.type])} />
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={cn(
                            'text-sm truncate',
                            notification.read ? 'text-virtus-text-secondary' : 'text-virtus-text-primary font-medium'
                          )}>
                            {notification.title}
                          </p>
                          
                          {/* Priority Indicator */}
                          {notification.priority === 'high' && (
                            <span className={cn(
                              'flex-shrink-0 w-2 h-2 rounded-full mt-1.5',
                              priorityColors[notification.priority]
                            )} />
                          )}
                        </div>
                        
                        <p className="text-xs text-virtus-text-muted line-clamp-2 mt-0.5">
                          {notification.message}
                        </p>
                        
                        <p className="text-[10px] text-virtus-text-muted mt-1">
                          {formatTime(notification.timestamp)}
                        </p>
                      </div>
                      
                      {/* Actions */}
                      <div className="flex-shrink-0 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {!notification.read && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              markAsRead(notification.id)
                            }}
                            className="p-1 text-virtus-text-muted hover:text-virtus-accent-success hover:bg-virtus-bg-tertiary rounded transition-colors"
                            title="Marcar como lida"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            deleteNotification(notification.id)
                          }}
                          className="p-1 text-virtus-text-muted hover:text-virtus-accent-danger hover:bg-virtus-bg-tertiary rounded transition-colors"
                          title="Remover"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          
          {/* Footer */}
          {notifications.length > 0 && (
            <div className="px-4 py-2 border-t border-virtus-border-primary">
              <button
                onClick={() => fetchNotifications()}
                className="w-full text-xs text-virtus-text-muted hover:text-virtus-accent-primary transition-colors"
              >
                Atualizar notificações
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
