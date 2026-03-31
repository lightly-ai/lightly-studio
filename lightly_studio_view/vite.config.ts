import { defineConfig, type Plugin } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import { writeFileSync } from 'fs';
import { join } from 'path';

// Plugin to report large chunks
function chunkSizeReporter(
    limitKb: number = 500,
    logFile: string = 'build-chunk-sizes.log'
): Plugin {
    return {
        name: 'chunk-size-reporter',
        enforce: 'post',
        generateBundle(_, bundle) {
            const largeChunks: Array<{ name: string; size: number; isLazyLoaded: boolean }> = [];

            for (const [fileName, chunk] of Object.entries(bundle)) {
                if (chunk.type === 'chunk') {
                    const sizeKb = Math.round(chunk.code.length / 1024);
                    // Determine if chunk is lazy-loaded based on whether it's dynamically imported
                    const isLazyLoaded = chunk.isDynamicEntry || !chunk.isEntry;
                    // Use higher limit for lazy-loaded chunks (like embedding-atlas)
                    const effectiveLimit = isLazyLoaded ? limitKb * 3 : limitKb;

                    if (sizeKb > effectiveLimit) {
                        largeChunks.push({ name: fileName, size: sizeKb, isLazyLoaded });
                    }
                }
            }

            if (largeChunks.length > 0) {
                const timestamp = new Date().toISOString();
                const logMessage = [
                    `[${timestamp}] WARNING: Large chunks detected!`,
                    ...largeChunks
                        .sort((a, b) => b.size - a.size)
                        .map(
                            ({ name, size, isLazyLoaded }) =>
                                `  ${name}: ${size} kB ${isLazyLoaded ? '(lazy-loaded, limit: ' + limitKb * 3 + ' kB)' : '(limit: ' + limitKb + ' kB)'}`
                        ),
                    ''
                ].join('\n');

                // Write to log file
                const logPath = join(process.cwd(), logFile);
                writeFileSync(logPath, logMessage + '\n', { flag: 'a' });

                // Also log to console
                console.error(
                    '\n⚠️  WARNING: Large chunks detected! See ' + logFile + ' for details.\n'
                );
            }
        }
    };
}

export default defineConfig({
    plugins: [sveltekit(), ...(process.env.REPORT_CHUNK_SIZES ? [chunkSizeReporter(500)] : [])],

    build: {
        rollupOptions: {
            output: {
                manualChunks(id) {
                    // Split embedding-atlas into its own chunk
                    if (id.includes('node_modules/embedding-atlas')) {
                        return 'vendor-embedding-atlas';
                    }
                    // Split apache-arrow into its own chunk
                    if (id.includes('node_modules/apache-arrow')) {
                        return 'vendor-apache-arrow';
                    }
                    // Split d3 libraries
                    if (id.includes('node_modules/d3-')) {
                        return 'vendor-d3';
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
