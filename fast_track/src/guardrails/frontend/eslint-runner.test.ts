import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('node:child_process', () => ({
    execFile: vi.fn()
}));

import { execFile } from 'node:child_process';
import { FRONTEND_ABS, FRONTEND_DIR, repoRelPath, runEslint } from './eslint-runner';

const mockExecFile = execFile as unknown as ReturnType<typeof vi.fn>;

type ExecCallback = (err: Error | null, result?: { stdout: string }) => void;

const succeed = (stdout: string) =>
    mockExecFile.mockImplementation(
        (_cmd: unknown, _args: unknown, _opts: unknown, cb: ExecCallback) => {
            cb(null, { stdout });
        }
    );

const failWith = (err: Error) =>
    mockExecFile.mockImplementation(
        (_cmd: unknown, _args: unknown, _opts: unknown, cb: ExecCallback) => {
            cb(err);
        }
    );

beforeEach(() => vi.clearAllMocks());

describe('repoRelPath', () => {
    it('converts an absolute ESLint path to a repo-relative path', () => {
        expect(repoRelPath(FRONTEND_ABS + '/src/foo.ts')).toBe(FRONTEND_DIR + '/src/foo.ts');
    });

    it('handles deeply nested paths', () => {
        expect(repoRelPath(FRONTEND_ABS + '/src/lib/bar/baz.ts')).toBe(
            FRONTEND_DIR + '/src/lib/bar/baz.ts'
        );
    });
});

describe('runEslint', () => {
    const sampleResults = [{ filePath: '/abs/path/src/foo.ts', messages: [] }];

    it('returns parsed JSON when ESLint exits cleanly', async () => {
        succeed(JSON.stringify(sampleResults));

        const result = await runEslint(['src/foo.ts'], 'eslint.config.js');

        expect(result).toEqual(sampleResults);
    });

    it('returns parsed JSON when ESLint exits with code 1 (lint errors found)', async () => {
        failWith(
            Object.assign(new Error('ESLint found errors'), {
                code: 1,
                stdout: JSON.stringify(sampleResults)
            })
        );

        const result = await runEslint(['src/foo.ts'], 'eslint.config.js');

        expect(result).toEqual(sampleResults);
    });

    it('rethrows when ESLint exits with a non-1 error code', async () => {
        failWith(Object.assign(new Error('fatal error'), { code: 2 }));

        await expect(runEslint(['src/foo.ts'], 'eslint.config.js')).rejects.toThrow('fatal error');
    });

    it('rethrows when the error has code 1 but stdout is not a string', async () => {
        failWith(Object.assign(new Error('no stdout'), { code: 1 }));

        await expect(runEslint(['src/foo.ts'], 'eslint.config.js')).rejects.toThrow('no stdout');
    });

    it('rethrows when the error has no code property', async () => {
        failWith(new Error('spawn failed'));

        await expect(runEslint(['src/foo.ts'], 'eslint.config.js')).rejects.toThrow('spawn failed');
    });

    it('passes --config, --format json, and file paths to ESLint', async () => {
        succeed('[]');

        await runEslint(['src/a.ts', 'src/b.ts'], 'eslint.config.js');

        const [, args] = mockExecFile.mock.calls[0];
        expect(args).toContain('--config');
        expect(args).toContain('eslint.config.js');
        expect(args).toContain('--format');
        expect(args).toContain('json');
        expect(args).toContain('src/a.ts');
        expect(args).toContain('src/b.ts');
    });

    it('inserts extra args between the fixed flags and the file list', async () => {
        succeed('[]');

        await runEslint(['src/a.ts'], 'eslint.config.js', ['--max-warnings', '0']);

        const [, args] = mockExecFile.mock.calls[0];
        const extraIndex = args.indexOf('--max-warnings');
        const fileIndex = args.indexOf('src/a.ts');
        expect(extraIndex).toBeGreaterThan(-1);
        expect(extraIndex).toBeLessThan(fileIndex);
    });
});
