import { paraglide } from '@inlang/paraglide-sveltekit/vite';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { defineConfig } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
    plugins: [
        sveltekit(),
        paraglide({
            project: './project.inlang',
            outdir: './src/lib/paraglide'
        }),
        monacoEditorPlugin.default({})
    ],

    test: {
        include: ['src/**/*.{test,spec}.{js,ts}']
    }
});
