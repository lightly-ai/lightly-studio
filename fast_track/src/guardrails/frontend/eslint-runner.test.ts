import { vi, describe, expect, it } from 'vitest';

const mockLintFiles = vi.fn();

// createRequire is called at module init time to load ESLint from the frontend package.
// Mocking node:module (hoisted by vitest) lets us intercept that before eslint-runner loads.
vi.mock('node:module', async (importOriginal) => {
    const actual = await importOriginal<typeof import('node:module')>();
    return {
        ...actual,
        createRequire: () => () => ({
            ESLint: vi.fn().mockImplementation(() => ({ lintFiles: mockLintFiles }))
        })
    };
});

import { runEslint, repoRelPath, FRONTEND_ABS } from './eslint-runner';

describe('repoRelPath', () => {
    it('converts an absolute path to a repo-relative path', () => {
        expect(repoRelPath(`${FRONTEND_ABS}/src/foo.ts`)).toBe('lightly_studio_view/src/foo.ts');
    });
});

describe('runEslint', () => {
    it('returns lintFiles results directly', async () => {
        const lintResult = {
            filePath: `${FRONTEND_ABS}/src/foo.ts`,
            messages: [
                {
                    ruleId: 'no-console',
                    severity: 2,
                    message: 'Unexpected console statement.',
                    line: 5,
                    column: 1,
                    endLine: 5,
                    endColumn: 20,
                    nodeType: 'CallExpression'
                }
            ],
            errorCount: 1,
            warningCount: 0,
            fixableErrorCount: 0,
            fixableWarningCount: 0,
            usedDeprecatedRules: []
        };
        mockLintFiles.mockResolvedValueOnce([lintResult]);

        const results = await runEslint(['src/foo.ts'], 'eslint.config.js');

        expect(results).toEqual([lintResult]);
    });

    it('returns empty messages array when there are no violations', async () => {
        const lintResult = {
            filePath: `${FRONTEND_ABS}/src/clean.ts`,
            messages: [],
            errorCount: 0,
            warningCount: 0
        };
        mockLintFiles.mockResolvedValueOnce([lintResult]);

        const results = await runEslint(['src/clean.ts'], 'eslint.config.js');

        expect(results).toEqual([lintResult]);
    });

    it('handles multiple files', async () => {
        mockLintFiles.mockResolvedValueOnce([
            { filePath: `${FRONTEND_ABS}/src/a.ts`, messages: [], errorCount: 0, warningCount: 0 },
            { filePath: `${FRONTEND_ABS}/src/b.ts`, messages: [], errorCount: 0, warningCount: 0 }
        ]);

        const results = await runEslint(['src/a.ts', 'src/b.ts'], 'eslint.config.js');

        expect(results).toHaveLength(2);
        expect(results[0]!.filePath).toBe(`${FRONTEND_ABS}/src/a.ts`);
        expect(results[1]!.filePath).toBe(`${FRONTEND_ABS}/src/b.ts`);
    });
});
