import { vi, describe, expect, it } from 'vitest';
import type { ESLint } from 'eslint';
import type { GuardrailContext } from '../context/types';
import { frontendComplexityGuardrail } from './complexity';
import { FRONTEND_ABS } from './eslint-runner';

vi.mock('node:fs', async (importOriginal) => {
    const actual = await importOriginal<typeof import('node:fs')>();
    return { ...actual, existsSync: vi.fn().mockReturnValue(true) };
});

vi.mock('./eslint-runner', async (importOriginal) => {
    const actual = await importOriginal<typeof import('./eslint-runner')>();
    return { ...actual, runEslint: vi.fn().mockResolvedValue([]) };
});

const { runEslint } = await import('./eslint-runner');
const { existsSync } = await import('node:fs');

const frontendFile = { path: 'lightly_studio_view/src/foo.ts', additions: 5, deletions: 0 };

function makeCtx(files = [frontendFile]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

describe('frontendComplexityGuardrail', () => {
    it('is required and runs locally', () => {
        expect(frontendComplexityGuardrail.required).toBe(true);
        expect(frontendComplexityGuardrail.needsPrContext).toBe(false);
    });

    it('passes immediately when no frontend files changed', async () => {
        const result = await frontendComplexityGuardrail.run(
            makeCtx([{ path: 'lightly_studio/src/model.py', additions: 5, deletions: 0 }])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s)');
    });

    it('passes when all changed frontend files are deleted', async () => {
        vi.mocked(existsSync).mockReturnValueOnce(false);
        const result = await frontendComplexityGuardrail.run(
            makeCtx([{ path: 'lightly_studio_view/src/deleted.ts', additions: 0, deletions: 10 }])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toBe('All changed frontend files were deleted.');
    });

    it('only lints existing files when some are deleted', async () => {
        vi.mocked(existsSync).mockReturnValueOnce(true).mockReturnValueOnce(false);
        vi.mocked(runEslint).mockResolvedValueOnce([
            { filePath: `${FRONTEND_ABS}/src/foo.ts`, messages: [] }
        ] as unknown as ESLint.LintResult[]);
        const result = await frontendComplexityGuardrail.run(
            makeCtx([
                { path: 'lightly_studio_view/src/foo.ts', additions: 5, deletions: 0 },
                { path: 'lightly_studio_view/src/deleted.ts', additions: 0, deletions: 10 }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('1 file(s) checked, no violations');
        expect(vi.mocked(runEslint)).toHaveBeenCalledWith(['src/foo.ts'], expect.any(String));
    });

    it('passes when ESLint reports no violations', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([
            { filePath: `${FRONTEND_ABS}/src/foo.ts`, messages: [] }
        ] as unknown as ESLint.LintResult[]);
        const result = await frontendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('1 file(s) checked, no violations');
    });

    it('passes when ESLint reports only warning-level messages', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([
            {
                filePath: `${FRONTEND_ABS}/src/foo.ts`,
                messages: [
                    { ruleId: 'complexity', severity: 1, message: 'Somewhat complex.', line: 5 }
                ]
            }
        ] as unknown as ESLint.LintResult[]);
        const result = await frontendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('no violations');
    });

    it('fails when ESLint reports an error-level violation', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([
            {
                filePath: `${FRONTEND_ABS}/src/foo.ts`,
                messages: [{ ruleId: 'complexity', severity: 2, message: 'Too complex.', line: 10 }]
            }
        ] as unknown as ESLint.LintResult[]);
        const result = await frontendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('lightly_studio_view/src/foo.ts:10 — Too complex.');
    });
});
