import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,  // 60s for video generation
});

export const fetchPosts = async () => {
  const { data } = await api.get('/posts');
  return data.items || [];
};

export const processRss = async () => {
  const { data } = await api.post('/process-rss');
  return data;
};

export const fetchRandomHeadlines = async (limit = 5) => {
  const { data } = await api.get('/headlines/random', { params: { limit } });
  return data.items || [];
};

export const generatePost = async (rssId, platform, template = 1) => {
  const { data } = await api.post('/generate/', { rss_id: rssId, platform, template });
  return data.item;  // unwrap from { item: {...} }
};

export const generateBatch = async (limit = 10) => {
  const { data } = await api.post('/generate/', { limit });
  return data;
};

export const retryPost = async (rssId) => {
  const { data } = await api.post('/retry/', { rss_id: rssId });
  return data;
};

export const uploadSelected = async (rssIds, platform) => {
  const { data } = await api.post('/upload-selected/', {
    rss_ids: rssIds,
    platform,
  });
  return data;
};

export const fetchDbStatus = async () => {
  const { data } = await api.get('/status');
  return data;
};
