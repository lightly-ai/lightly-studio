import { defineConfig, type Plugin } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import { writeFileSync } from 'fs';
import { join } from 'path';

// Plugin to report large chunks
function chunkSizeReporter(limitKb: number = 500, logFile: string = 'build-chunk-sizes.log'): Plugin {
    return {
        name: 'chunk-size-reporter',
        enforce: 'post',
        generateBundle(_, bundle) {
            const largeChunks: Array<{ name: string; size: number }> = [];

            for (const [fileName, chunk] of Object.entries(bundle)) {
                if (chunk.type === 'chunk') {
                    const sizeKb = Math.round(chunk.code.length / 1024);
                    if (sizeKb > limitKb) {
                        largeChunks.push({ name: fileName, size: sizeKb });
                    }
                }
            }

            if (largeChunks.length > 0) {
                const timestamp = new Date().toISOString();
                const logMessage = [
                    `[${timestamp}] WARNING: Large chunks detected!`,
                    ...largeChunks
                        .sort((a, b) => b.size - a.size)
                        .map(({ name, size }) => `  ${name}: ${size} kB (limit: ${limitKb} kB)`),
                    ''
                ].join('\n');

                // Write to log file
                const logPath = join(process.cwd(), logFile);
                writeFileSync(logPath, logMessage + '\n', { flag: 'a' });

                // Also log to console
                console.error('\n⚠️  WARNING: Large chunks detected! See ' + logFile + ' for details.\n');
            }
        }
    };
}

export default defineConfig({
    plugins: [
        sveltekit(),
        ...(process.env.REPORT_CHUNK_SIZES ? [chunkSizeReporter(500)] : [])
    ],

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
