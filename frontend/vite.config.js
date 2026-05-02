import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/posts': 'http://localhost:8000',
      '/process-rss': 'http://localhost:8000',
      '/generate': 'http://localhost:8000',
      '/retry': 'http://localhost:8000',
      '/upload-selected': 'http://localhost:8000',
      '/headlines': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/generated': 'http://localhost:8000',
    },
  },
});
