import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';

import path from 'path';

export default defineConfig({
    plugins: [sveltekit()],
    esbuild: {
        // Transpile all files with ESBuild to remove comments from code coverage.
        // Required for `test.coverage.ignoreEmptyLines` to work:
        include: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.ts', '**/*.tsx']
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['src/setupTests.ts'],
        coverage: {
            provider: 'v8',
            ignoreEmptyLines: true
        }
    },
    resolve: {
        conditions: ['browser'],
        alias: {
            '@': path.resolve(__dirname, 'src'),
            $lib: path.resolve(__dirname, 'src/lib'),
            '$env/static/public': path.resolve(__dirname, '.env')
        }
    }
});
