import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
    plugins: [sveltekit()],

    build: {
        rollupOptions: {
            output: {
                manualChunks: undefined // Let SvelteKit handle chunking
            }
        },
        chunkSizeWarningLimit: 500
    },

    test: {
        include: ['src/**/*.{test,spec}.{js,ts}']
    }
});
