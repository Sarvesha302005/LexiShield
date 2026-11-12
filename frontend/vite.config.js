import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';

const outDir = path.resolve(__dirname, '../src/static');

// Bundles get a new hashed name every build, so clear the old ones out of assets/ first.
// Only assets/ is cleared; the rest of src/static is left alone.
const cleanAssets = () => ({
  name: 'clean-static-assets',
  apply: 'build',
  buildStart() {
    fs.rmSync(path.join(outDir, 'assets'), { recursive: true, force: true });
  },
});

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), cleanAssets()],
  build: {
    outDir,
    emptyOutDir: false, // Don't wipe everything unexpectedly
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
