import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import posthogRollupPlugin from '@posthog/rollup-plugin';
import { readFileSync } from 'node:fs';

interface VersionInfo {
    version: string;
}

function readVersion(): string {
    const contents = readFileSync(new URL('./src/lib/version.json', import.meta.url), 'utf8');
    const versionInfo = JSON.parse(contents) as VersionInfo;
    return versionInfo.version;
}

const version = readVersion();

function createPosthogPlugin(): ReturnType<typeof posthogRollupPlugin> | null {
    const personalApiKey = process.env.POSTHOG_PERSONAL_API_KEY;
    const projectId = process.env.POSTHOG_PROJECT_ID;
    const host = process.env.POSTHOG_HOST;
    if (!personalApiKey || !projectId || !host) return null;

    return posthogRollupPlugin({
        personalApiKey,
        projectId,
        host,
        sourcemaps: {
            releaseVersion: version,
            deleteAfterUpload: true
        }
    });
}

const posthogPlugin = createPosthogPlugin();

export default defineConfig({
    plugins: [sveltekit(), ...(posthogPlugin ? [posthogPlugin] : [])],

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
});
