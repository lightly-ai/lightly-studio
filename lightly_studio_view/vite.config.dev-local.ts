// TEMPORARY dev-only config (untracked). Serves this worktree's live frontend and
// proxies API/media to the already-running :8001 backend that has a dataset loaded.
// Delete when done: rm lightly_studio_view/vite.config.dev-local.ts
import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

const backend = 'http://localhost:8001';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        port: 5173,
        strictPort: true,
        proxy: {
            '/api': { target: backend, changeOrigin: true },
            '/images': { target: backend, changeOrigin: true },
            '/videos': { target: backend, changeOrigin: true },
            '/frames': { target: backend, changeOrigin: true }
        }
    }
});
