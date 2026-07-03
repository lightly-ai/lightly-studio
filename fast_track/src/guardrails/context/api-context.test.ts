import { describe, expect, it, vi } from 'vitest';

import { ApiGuardrailContext, toChangedFile, type ApiFile } from './api-context';
import type { Octokit } from './types';

/**
 * A minimal Octokit stand-in: `paginate` resolves to the given files and
 * records its arguments; `rest.pulls.listFiles` is an opaque marker that
 * `paginate` is asked to walk.
 */
function fakeOctokit(files: ApiFile[]): {
    octokit: Octokit;
    paginate: ReturnType<typeof vi.fn>;
    listFiles: unknown;
} {
    const listFiles = Symbol('pulls.listFiles');
    const paginate = vi.fn(async () => files);
    const octokit = {
        paginate,
        rest: { pulls: { listFiles } }
    } as unknown as Octokit;
    return { octokit, paginate, listFiles };
}

describe('toChangedFile', () => {
    it('maps filename/additions/deletions and keeps the patch', () => {
        expect(
            toChangedFile({ filename: 'src/a.ts', additions: 3, deletions: 1, patch: '@@ hunk @@' })
        ).toEqual({ path: 'src/a.ts', additions: 3, deletions: 1, patch: '@@ hunk @@' });
    });

    it('omits the patch field entirely when the API omits it (binary/large)', () => {
        const result = toChangedFile({ filename: 'logo.png', additions: 0, deletions: 0 });
        expect(result).toEqual({ path: 'logo.png', additions: 0, deletions: 0 });
        expect('patch' in result).toBe(false);
    });
});

describe('ApiGuardrailContext', () => {
    const pr = { owner: 'acme', repo: 'widgets', pull_number: 42 };

    it('paginates listFiles with the PR params and runs results through the mapper', async () => {
        const { octokit, paginate, listFiles } = fakeOctokit([
            { filename: 'a.ts', additions: 2, deletions: 0, patch: '@@ a @@' }
        ]);
        const context = new ApiGuardrailContext(octokit, pr, 'main');

        // Mapping semantics (patch present/absent) are owned by the toChangedFile
        // tests; here we only assert results are mapped (path, not filename).
        expect(await context.changedFiles()).toEqual([
            { path: 'a.ts', additions: 2, deletions: 0, patch: '@@ a @@' }
        ]);
        expect(paginate).toHaveBeenCalledWith(listFiles, {
            owner: 'acme',
            repo: 'widgets',
            pull_number: 42,
            per_page: 100
        });
    });

    it('exposes the base ref and the octokit client to guardrails', () => {
        const { octokit } = fakeOctokit([]);
        const context = new ApiGuardrailContext(octokit, pr, 'release/2.0');
        expect(context.baseRef).toBe('release/2.0');
        expect(context.octokit).toBe(octokit);
    });

    it('fetches only once across repeated calls (memoized)', async () => {
        const { octokit, paginate } = fakeOctokit([]);
        const context = new ApiGuardrailContext(octokit, pr, 'main');
        await context.changedFiles();
        await context.changedFiles();
        expect(paginate).toHaveBeenCalledTimes(1);
    });
});
