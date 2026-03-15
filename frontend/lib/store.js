import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

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

const applicationInitialState = {
  currentApplicationId: null,
  currentLoanType: null,
  messages: [],
  workflowStage: null,
  applicationStatus: null,
  loanOffer: null,
  loanId: null,
  isCompleted: false,
  isLoading: false,
};

// Application Store
export const useApplicationStore = create(
  persist(
    (set) => ({
      ...applicationInitialState,
      setCurrentApplication: (id, loanType = null) =>
        set((state) => ({
          currentApplicationId: id,
          currentLoanType: loanType ?? state.currentLoanType,
        })),
      setApplicationSnapshot: ({
        applicationId,
        loanType,
        messages,
        stage,
        status,
        loanOffer,
        loanId,
        isCompleted,
      }) =>
        set((state) => ({
          currentApplicationId: applicationId ?? state.currentApplicationId,
          currentLoanType: loanType ?? state.currentLoanType,
          messages: messages ?? state.messages,
          workflowStage: stage ?? state.workflowStage,
          applicationStatus: status ?? state.applicationStatus,
          loanOffer: loanOffer ?? state.loanOffer,
          loanId: loanId ?? state.loanId,
          isCompleted: isCompleted ?? state.isCompleted,
        })),
      addMessage: (message) =>
        set((state) => ({ messages: [...state.messages, message] })),
      setMessages: (messages) => set({ messages }),
      setWorkflowStage: (workflowStage) => set({ workflowStage }),
      setApplicationStatus: (applicationStatus) => set({ applicationStatus }),
      setLoanOffer: (loanOffer) => set({ loanOffer }),
      setLoanId: (loanId) => set({ loanId }),
      setCompleted: (isCompleted) => set({ isCompleted }),
      clearMessages: () => set({ ...applicationInitialState }),
      setLoading: (isLoading) => set({ isLoading }),
    }),
    {
      name: 'loan-application-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        currentApplicationId: state.currentApplicationId,
        currentLoanType: state.currentLoanType,
        messages: state.messages,
        workflowStage: state.workflowStage,
        applicationStatus: state.applicationStatus,
        loanOffer: state.loanOffer,
        loanId: state.loanId,
        isCompleted: state.isCompleted,
      }),
    }
  )
);

// UI Store
export const useUIStore = create((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  closeSidebar: () => set({ sidebarOpen: false }),
  openSidebar: () => set({ sidebarOpen: true }),
}));
