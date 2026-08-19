import { createRequire } from 'node:module';
import type { ESLint } from 'eslint';
import { FRONTEND_ABS, FRONTEND_DIR } from './shared';

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
