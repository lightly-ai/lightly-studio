import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
// import { join } from 'path';
// import { fileURLToPath } from 'node:url';

export default defineConfig({
    plugins: [sveltekit()],
    worker: {
        // `monaco-languageclient` worker build cannot use `iife` with
        // code-splitting, so force ESM workers for production bundling.
        format: 'es'
    },
    // server: {
    //     fs: {
    //         allow: ['../../', '../../../vscode']
    //     }
    // },
    resolve: {
        // `monaco-languageclient` wires its services into
        // 'monaco-editor': '@codingame/monaco-vscode-editor-api'
        // alias: [
        //     {
        //         find: 'monaco-editor-core/esm/vs',
        //         replacement: join(__dirname, '../../../vscode/src/vs')
        //     },
        //     {
        //         find: 'monaco-editor-core',
        //         replacement: join(__dirname, '../../../vscode/src/vs/editor/editor.main.ts')
        //     }
        // ]
    },

    // resolve: {
    //     alias: {
    //         // `monaco-languageclient` wires its services into
    //         'monaco-editor': '@codingame/monaco-vscode-editor-api',
    //         '@codingame/monaco-vscode-api/vscode/vs/base/browser/cssValue': fileURLToPath(
    //             new URL(
    //                 './node_modules/@codingame/monaco-vscode-api/vscode/src/vs/base/browser/cssValue.js',
    //                 import.meta.url
    //             )
    //         )
    //     }
    // },

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
