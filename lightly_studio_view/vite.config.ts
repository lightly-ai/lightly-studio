import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
    plugins: [sveltekit()],
    server: {
        proxy: {
            '/images': {
                target: 'http://localhost:8001',
                changeOrigin: true
            }
        }
    },

    test: {
        include: ['src/**/*.{test,spec}.{js,ts}']
    }
});
