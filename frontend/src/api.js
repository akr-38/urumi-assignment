import axios from 'axios';

// In production (K8s), we rely on Nginx reverse proxy at /api
// In local dev, Vite proxies /api to localhost:8000
const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getStores = async () => {
  const response = await api.get('/stores');
  return response.data;
};

export const createStore = async (name, type) => {
  const response = await api.post('/stores', { name, type });
  return response.data;
};

export const deleteStore = async (name) => {
  const response = await api.delete(`/stores/${name}`);
  return response.data;
};

export default api;
