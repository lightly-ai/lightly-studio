import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { ESLint } from 'eslint';

const __dirname = dirname(fileURLToPath(import.meta.url));

export const FRONTEND_DIR = 'lightly_studio_view';
// fast_track/src/guardrails/frontend -> fast_track/src/guardrails -> fast_track -> repo root -> lightly_studio_view
export const FRONTEND_ABS = resolve(__dirname, '../../../..', FRONTEND_DIR);
export const FRONTEND_PREFIX = FRONTEND_DIR + '/';

// Converts an absolute ESLint file path to a repo-relative path (e.g. lightly_studio_view/src/foo.ts).
export function repoRelPath(absPath: string): string {
    return FRONTEND_DIR + '/' + absPath.slice(FRONTEND_ABS.length + 1);
}

export async function runEslint(relPaths: string[], config: string): Promise<ESLint.LintResult[]> {
    // Load ESLint lazily from the frontend package so its config plugins resolve correctly.
    // Lazy loading also avoids a top-level require at import time, which would break tests
    // that mock this module via importOriginal (eslint is not installed in fast_track).
    const require = createRequire(FRONTEND_ABS + '/package.json');
    const { ESLint: FrontendESLint } = require('eslint') as { ESLint: typeof ESLint };
    const eslint = new FrontendESLint({
        cwd: FRONTEND_ABS,
        overrideConfigFile: config
    });
    return eslint.lintFiles(relPaths);
}
