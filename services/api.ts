import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

const API_URL = 'http://localhost:8000/api/v1';

export const createAPI = (): AxiosInstance => {
  const api = axios.create({
    baseURL: API_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  api.interceptors.request.use((config: AxiosRequestConfig) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return api;
};

export const api = createAPI();

export default api; 