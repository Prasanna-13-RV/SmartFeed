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

export const uploadCookies = async (file) => {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/clips/upload-cookies', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const getAllClips = async () => {
  const { data } = await api.get('/clips');
  return data; // { videos: [{video_id, total, links}], total_videos, total_clips }
};

export const processClips = async (urls, clipDuration = null) => {
  const { data } = await api.post('/clips/process', { urls, clip_duration: clipDuration }, {
    timeout: 600000, // 10 min — video processing can take a while
  });
  return data; // { video_id: [links...] }
};

export const getClips = async (videoId) => {
  const { data } = await api.get(`/clips/${videoId}`);
  return data;
};

export const deleteClips = async (videoId) => {
  const { data } = await api.delete(`/clips/${videoId}`);
  return data;
};
