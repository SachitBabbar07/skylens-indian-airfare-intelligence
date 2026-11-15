import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({plugins:[react()],server:{proxy:Object.fromEntries(['/health','/model-info','/airports','/supported-options','/coverage','/route-coverage','/airlines','/predict','/explain','/feature-importance'].map(p=>[p,'http://127.0.0.1:8000']))}});
