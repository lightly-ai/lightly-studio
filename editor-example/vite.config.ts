import { defineConfig } from 'vite';

export default defineConfig({
  worker: {
    format: 'es'
  },
  build: {
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ['monaco-editor']
        }
      }
    }
  },
  optimizeDeps: {
    include: ['monaco-editor']
  }
});
