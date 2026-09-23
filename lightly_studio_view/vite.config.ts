import { defineConfig } from 'vitest/config';
import { loadEnv } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), 'PUBLIC_');
    return {
        plugins: [sveltekit()],
        server: {
            proxy: {
                '/images': {
                    // Canvas pixel access needs same-origin images during frontend development.
                    target: env.PUBLIC_SAMPLES_URL || 'http://localhost:8001/images',
                    rewrite: (path) => path.replace(/^\/images/, ''),
                    changeOrigin: true
                }
            }
        },

        build: {
            rollupOptions: {
                output: {
                    manualChunks(id) {
                        // Keep the preload helper in the base vendor chunk to avoid circular initialization.
                        if (id.includes('vite/preload-helper')) {
                            return 'vendor';
                        }
                        // Split embedding-atlas into its own chunk
                        if (id.includes('node_modules/embedding-atlas')) {
                            return 'vendor-embedding-atlas';
                        }
                        // Split apache-arrow into its own chunk
                        if (id.includes('node_modules/apache-arrow')) {
                            return 'vendor-apache-arrow';
                        }
                        // Split monaco-editor into its own chunk so it stays lazy (only the
                        // dynamically imported QueryEditorPanel pulls it) instead of riding the
                        // eager `vendor` chunk that posthog-js keeps on every route.
                        if (id.includes('node_modules/monaco-editor')) {
                            return 'vendor-monaco';
                        }
                        // Split d3 libraries
                        if (id.includes('node_modules/d3-')) {
                            return 'vendor-d3';
                        }
                        // Split echarts (and its zrender rendering engine)
                        if (
                            id.includes('node_modules/echarts') ||
                            id.includes('node_modules/zrender')
                        ) {
                            return 'vendor-echarts';
                        }
                        // Split tanstack query
                        if (id.includes('node_modules/@tanstack')) {
                            return 'vendor-tanstack';
                        }
                        // Split svelte ecosystem
                        if (
                            id.includes('node_modules/svelte-') ||
                            id.includes('node_modules/bits-ui') ||
                            id.includes('node_modules/paneforge')
                        ) {
                            return 'vendor-svelte-ui';
                        }
                        // Split lodash
                        if (id.includes('node_modules/lodash')) {
                            return 'vendor-lodash';
                        }
                        // Group other large vendor libraries
                        if (id.includes('node_modules')) {
                            return 'vendor';
                        }
                    }
                }
            },
            chunkSizeWarningLimit: 500
        },

        test: {
            include: ['src/**/*.{test,spec}.{js,ts}']
        }
    }
});
