import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

const backendPaths = ['/acquisition', '/flights', '/research/', '/capabilities', '/fare-estimate', '/health',
  '/model-info', '/airports', '/supported-options', '/coverage', '/route-coverage', '/airlines', '/predict',
  '/explain', '/feature-importance', '/fare-semantics', '/docs', '/openapi.json'];

export default defineConfig({
  plugins: [react()],
  build: {rollupOptions: {input: ['index.html', 'research.html']}},
  server: {proxy: Object.fromEntries(backendPaths.map(path => [path, 'http://127.0.0.1:8000']))},
});
