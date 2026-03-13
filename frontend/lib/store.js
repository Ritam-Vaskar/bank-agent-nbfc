import { create } from 'zustand';

// Auth Store (without persistence for SSR compatibility)
export const useAuthStore = create((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isAuthInitialized: false,
  setAuth: (user, token) => {
    set({ user, token, isAuthenticated: true, isAuthInitialized: true });
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
    }
  },
  clearAuth: () => {
    set({ user: null, token: null, isAuthenticated: false, isAuthInitialized: true });
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  },
  // Initialize from localStorage on client
  initAuth: () => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');
      if (token && userStr) {
        try {
          const user = JSON.parse(userStr);
          set({ user, token, isAuthenticated: true, isAuthInitialized: true });
        } catch (e) {
          console.error('Failed to parse stored user:', e);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          set({ user: null, token: null, isAuthenticated: false, isAuthInitialized: true });
        }
      } else {
        set({ user: null, token: null, isAuthenticated: false, isAuthInitialized: true });
      }
    } else {
      set({ isAuthInitialized: true });
    }
  },
}));

// Application Store
export const useApplicationStore = create((set) => ({
  currentApplicationId: null,
  messages: [],
  isLoading: false,
  setCurrentApplication: (id) => set({ currentApplicationId: id }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setMessages: (messages) => set({ messages }),
  clearMessages: () => set({ messages: [], currentApplicationId: null }),
  setLoading: (isLoading) => set({ isLoading }),
}));

// UI Store
export const useUIStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  closeSidebar: () => set({ sidebarOpen: false }),
  openSidebar: () => set({ sidebarOpen: true }),
}));
