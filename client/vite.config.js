import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Forward API calls to the Express server during development.
    // 127.0.0.1, not localhost: localhost can resolve to ::1, where another app may hold port 3001.
    proxy: { '/api': 'http://127.0.0.1:3001' },
  },
});
