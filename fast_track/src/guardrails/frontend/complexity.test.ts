import { vi, describe, expect, it } from 'vitest';
import type { ESLint } from 'eslint';
import type { GuardrailContext } from '../context/types';
import { frontendComplexityGuardrail } from './complexity';
import { FRONTEND_ABS } from './eslint-runner';

vi.mock('./eslint-runner', async (importOriginal) => {
    const actual = await importOriginal<typeof import('./eslint-runner')>();
    return { ...actual, runEslint: vi.fn().mockResolvedValue([]) };
});

const { runEslint } = await import('./eslint-runner');

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

    it('passes when ESLint reports no violations', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([
            { filePath: `${FRONTEND_ABS}/src/foo.ts`, messages: [] }
        ] as unknown as ESLint.LintResult[]);
        const result = await frontendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('1 file(s) checked, no violations');
    });

    it('passes when a deleted frontend file is in changedFiles', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([]);
        const result = await frontendComplexityGuardrail.run(
            makeCtx([{ path: 'lightly_studio_view/src/deleted.ts', additions: 0, deletions: 10 }])
        );
        expect(result.status).toBe('pass');
    });

    it('passes when ESLint reports only warning-level messages', async () => {
        vi.mocked(runEslint).mockResolvedValueOnce([
            {
                filePath: `${FRONTEND_ABS}/src/foo.ts`,
                messages: [{ ruleId: 'complexity', severity: 1, message: 'Somewhat complex.', line: 5 }]
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
