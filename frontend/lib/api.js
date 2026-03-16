import axios from 'axios';
import toast from 'react-hot-toast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor - Add auth token  
api.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (window.location.pathname !== '/') {
          toast.error('Session expired. Please login again.');
          window.location.href = '/';
        }
      }
    } else if (error.response?.status !== 404) {
      toast.error(message);
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  requestOTP: (email) => api.post('/request-otp', { email }),
  verifyOTP: (email, otp) => api.post('/verify-otp', { email, otp }),
  getProfile: () => api.get('/me'),
  logout: () => api.post('/logout'),
};

// Loans API
export const loansAPI = {
  applyForLoan: (loanType) => api.post('/loans/apply', null, { params: { loan_type: loanType } }),
  sendMessage: (applicationId, message) => 
    api.post(`/loans/applications/${applicationId}/chat`, { message }),
  terminateChat: (applicationId) => api.post(`/loans/applications/${applicationId}/terminate`),
  resetChat: (applicationId) => api.post(`/loans/applications/${applicationId}/reset`),
  getApplications: (status) => api.get('/loans/applications', { params: status ? { status } : {} }),
  getApplication: (applicationId) => api.get(`/loans/applications/${applicationId}`),
  getActiveLoans: () => api.get('/loans/active'),
  getLoanDetails: (loanId) => api.get(`/loans/${loanId}`),
  getEMISchedule: (loanId) => api.get(`/loans/${loanId}/emi-schedule`),
  downloadSanctionLetter: (loanId) => 
    api.get(`/loans/${loanId}/sanction-letter`, { responseType: 'blob' }),
};

// Health check
export const healthCheck = () => axios.get(`${API_URL}/health`);

export default api;
