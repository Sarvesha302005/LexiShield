import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

const isVercel = Boolean(process.env.VERCEL);
const outDir = isVercel
  ? path.resolve(__dirname, 'dist')
  : path.resolve(__dirname, '../src/static');

// Bundles get a new hashed name every build, so clear the old ones out of assets/ first.
// Only assets/ is cleared; the rest of src/static is left alone.
const cleanAssets = () => ({
  name: 'clean-static-assets',
  apply: 'build',
  buildStart() {
    const assetsPath = path.join(outDir, 'assets');
    if (fs.existsSync(assetsPath)) {
      fs.rmSync(assetsPath, { recursive: true, force: true });
    }
  },
});

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), cleanAssets()],
  build: {
    outDir,
    emptyOutDir: isVercel,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
