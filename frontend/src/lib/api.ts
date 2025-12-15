import axios from 'axios';
import { setupHttpLogging, loggers } from './logger';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// Auth token interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    loggers.auth.debug('Auth token attached to request');
  }
  return config;
});

// Setup HTTP logging interceptors
setupHttpLogging(api, loggers.api);

export default api;
