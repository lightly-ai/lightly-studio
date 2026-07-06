import { vi, describe, expect, it } from 'vitest';
import { resolve } from 'node:path';
import type { ChildProcess } from 'node:child_process';
import type { ChangedFile, GuardrailContext } from '../context/types';
import { backendComplexityGuardrail } from './complexity';
import { REPO_ROOT } from './shared';

type PromisifyCb = (error: Error | null, result?: { stdout: string }) => void;

vi.mock('node:child_process', async (importOriginal) => {
    const actual = await importOriginal<typeof import('node:child_process')>();
    return { ...actual, execFile: vi.fn() };
});

vi.mock('node:fs', async (importOriginal) => {
    const actual = await importOriginal<typeof import('node:fs')>();
    return { ...actual, existsSync: vi.fn().mockReturnValue(true) };
});

const { execFile } = await import('node:child_process');
const { existsSync } = await import('node:fs');

const backendFile: ChangedFile = {
    path: 'lightly_studio/src/model.py',
    status: 'modified',
    additions: 5,
    deletions: 0
};

function makeCtx(files: ChangedFile[] = [backendFile]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

describe('backendComplexityGuardrail', () => {
    it('is required and runs locally', () => {
        expect(backendComplexityGuardrail.required).toBe(true);
        expect(backendComplexityGuardrail.needsPrContext).toBe(false);
    });

    it('passes immediately when no backend files changed', async () => {
        const result = await backendComplexityGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio_view/src/foo.ts',
                    status: 'modified',
                    additions: 5,
                    deletions: 0
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s)');
    });

    it('passes when ruff reports no violations', async () => {
        vi.mocked(execFile).mockImplementationOnce((_cmd, _args, _opts, cb) => {
            (cb as unknown as PromisifyCb)(null, { stdout: '[]' });
            return undefined as unknown as ChildProcess;
        });
        const result = await backendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('1 file(s) checked, no violations');
    });

    it('fails when ruff reports a C901 violation', async () => {
        const ruffOutput = JSON.stringify([
            {
                code: 'C901',
                filename: resolve(REPO_ROOT, 'lightly_studio/src/model.py'),
                message: 'Function `foo` is too complex (11 > 10)',
                location: { row: 42, column: 0 }
            }
        ]);
        const err = Object.assign(new Error(), { code: 1, stdout: ruffOutput });
        vi.mocked(execFile).mockImplementationOnce((_cmd, _args, _opts, cb) => {
            (cb as unknown as PromisifyCb)(err);
            return undefined as unknown as ChildProcess;
        });
        const result = await backendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('fail');
        expect(result.summary).toContain(
            'lightly_studio/src/model.py:42 — Function `foo` is too complex (11 > 10)'
        );
    });

    it('passes for a deleted backend file (does not exist on disk)', async () => {
        vi.mocked(existsSync).mockReturnValueOnce(false);
        const result = await backendComplexityGuardrail.run(makeCtx());
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('deleted');
    });
});
