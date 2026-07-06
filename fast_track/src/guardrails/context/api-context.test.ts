import { describe, expect, it } from 'vitest';

import type { Octokit } from './api-context';
import { ApiGuardrailContext, toChangedFile } from './api-context';

/** A `pulls.listFiles` entry, with the extra fields the mapper ignores. */
function listedFile(filename: string, additions: number, deletions: number) {
    return { filename, additions, deletions, status: 'modified', patch: '@@ ... @@' };
}

/**
 * A fake Octokit whose `paginate` returns `files` (as the real one does after
 * walking every page) and records each call in `paginateCalls`. `listFiles` is a
 * sentinel so a test can assert we hand *that* endpoint to `paginate`.
 */
function fakeOctokit(files: ReturnType<typeof listedFile>[]) {
    const paginateCalls: { endpoint: unknown; params: unknown }[] = [];
    const octokit = {
        rest: { pulls: { listFiles: 'listFiles-endpoint' } },
        paginate: async (endpoint: unknown, params: unknown) => {
            paginateCalls.push({ endpoint, params });
            return files;
        }
    } as unknown as Octokit;
    return { octokit, paginateCalls };
}

describe('toChangedFile', () => {
    it('keeps counts and drops the rest', () => {
        expect(toChangedFile(listedFile('src/foo.ts', 12, 3))).toEqual({
            path: 'src/foo.ts',
            additions: 12,
            deletions: 3
        });
    });
});

describe('ApiGuardrailContext', () => {
    it('rejects an empty base ref', () => {
        const { octokit } = fakeOctokit([]);
        expect(
            () =>
                new ApiGuardrailContext({
                    octokit,
                    owner: 'acme',
                    repo: 'widgets',
                    prNumber: 1,
                    baseRef: '  '
                })
        ).toThrow(/must not be empty/);
    });

    it('paginates listFiles with the PR coordinates and maps to counts', async () => {
        const { octokit, paginateCalls } = fakeOctokit([
            listedFile('a.ts', 1, 0),
            listedFile('b.ts', 0, 5)
        ]);
        const context = new ApiGuardrailContext({
            octokit,
            owner: 'acme',
            repo: 'widgets',
            prNumber: 42,
            baseRef: 'main'
        });

        expect(await context.changedFiles()).toEqual([
            { path: 'a.ts', additions: 1, deletions: 0 },
            { path: 'b.ts', additions: 0, deletions: 5 }
        ]);
        expect(paginateCalls).toEqual([
            {
                endpoint: octokit.rest.pulls.listFiles,
                params: { owner: 'acme', repo: 'widgets', pull_number: 42, per_page: 100 }
            }
        ]);
    });

    it('memoizes: repeated changedFiles() calls hit the API once', async () => {
        const { octokit, paginateCalls } = fakeOctokit([listedFile('a.ts', 1, 0)]);
        const context = new ApiGuardrailContext({
            octokit,
            owner: 'acme',
            repo: 'widgets',
            prNumber: 7,
            baseRef: 'main'
        });

        const [first, second] = await Promise.all([context.changedFiles(), context.changedFiles()]);
        await context.changedFiles();

        expect(first).toEqual(second);
        expect(paginateCalls).toHaveLength(1);
    });
});
