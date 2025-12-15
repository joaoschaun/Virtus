import { create } from 'zustand'
import { api } from '../services/api'

export type NotificationType = 'trade' | 'alert' | 'bot' | 'news' | 'system'
export type NotificationPriority = 'low' | 'medium' | 'high'

export interface Notification {
  id: string
  type: NotificationType
  priority: NotificationPriority
  title: string
  message: string
  timestamp: string
  read: boolean
  data?: Record<string, any>
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  isLoading: boolean
  isOpen: boolean
  
  // Actions
  fetchNotifications: () => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markAsRead: (id: string) => Promise<void>
  markAllAsRead: () => Promise<void>
  deleteNotification: (id: string) => Promise<void>
  clearAll: () => Promise<void>
  setOpen: (open: boolean) => void
  toggleOpen: () => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isLoading: false,
  isOpen: false,
  
  fetchNotifications: async () => {
    set({ isLoading: true })
    try {
      const response = await api.get('/api/notifications?limit=50')
      set({
        notifications: response.data.notifications,
        unreadCount: response.data.unread_count,
      })
    } catch (error) {
      console.error('Failed to fetch notifications:', error)
    } finally {
      set({ isLoading: false })
    }
  },
  
  fetchUnreadCount: async () => {
    try {
      const response = await api.get('/api/notifications/unread-count')
      set({ unreadCount: response.data.unread_count })
    } catch (error) {
      console.error('Failed to fetch unread count:', error)
    }
  },
  
  markAsRead: async (id: string) => {
    try {
      await api.post(`/api/notifications/${id}/read`)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }))
    } catch (error) {
      console.error('Failed to mark as read:', error)
    }
  },
  
  markAllAsRead: async () => {
    try {
      await api.post('/api/notifications/read-all')
      set((state) => ({
        notifications: state.notifications.map((n) => ({ ...n, read: true })),
        unreadCount: 0,
      }))
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  },
  
  deleteNotification: async (id: string) => {
    try {
      await api.delete(`/api/notifications/${id}`)
      const notification = get().notifications.find((n) => n.id === id)
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
        unreadCount: notification && !notification.read 
          ? Math.max(0, state.unreadCount - 1) 
          : state.unreadCount,
      }))
    } catch (error) {
      console.error('Failed to delete notification:', error)
    }
  },
  
  clearAll: async () => {
    try {
      await api.delete('/api/notifications')
      set({ notifications: [], unreadCount: 0 })
    } catch (error) {
      console.error('Failed to clear notifications:', error)
    }
  },
  
  setOpen: (open: boolean) => set({ isOpen: open }),
  
  toggleOpen: () => set((state) => ({ isOpen: !state.isOpen })),
}))
