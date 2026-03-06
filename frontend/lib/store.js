import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// Auth Store
export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => {
        set({ user, token, isAuthenticated: true });
        if (typeof window !== 'undefined') {
          localStorage.setItem('token', token);
          localStorage.setItem('user', JSON.stringify(user));
        }
      },
      clearAuth: () => {
        set({ user: null, token: null, isAuthenticated: false });
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => 
        typeof window !== 'undefined' ? localStorage : undefined
      ),
    }
  )
);

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
