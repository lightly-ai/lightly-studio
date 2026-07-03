import { describe, expect, it, vi } from 'vitest';

import { ApiGuardrailContext, toChangedFile } from './api-context';
import type { Octokit } from './types';

interface ApiFileLike {
    filename: string;
    additions: number;
    deletions: number;
    patch?: string;
}

interface ListFilesParams {
    owner: string;
    repo: string;
    pull_number: number;
    per_page: number;
    page: number;
}

/**
 * A minimal Octokit whose `pulls.listFiles` serves canned pages: `pages[0]` is
 * page 1, `pages[1]` is page 2, and so on; a page past the end resolves empty.
 * The `listFiles` mock is returned too so tests can assert the request params.
 */
function fakeOctokit(pages: ApiFileLike[][]): {
    octokit: Octokit;
    listFiles: ReturnType<typeof vi.fn>;
} {
    const listFiles = vi.fn(async (params: ListFilesParams) => ({
        data: pages[params.page - 1] ?? []
    }));
    const octokit = { rest: { pulls: { listFiles } } } as unknown as Octokit;
    return { octokit, listFiles };
}

function makeFile(name: string, overrides: Partial<ApiFileLike> = {}): ApiFileLike {
    return { filename: name, additions: 1, deletions: 0, ...overrides };
}

function contextOver(pages: ApiFileLike[][]): {
    context: ApiGuardrailContext;
    listFiles: ReturnType<typeof vi.fn>;
} {
    const { octokit, listFiles } = fakeOctokit(pages);
    const context = new ApiGuardrailContext({
        octokit,
        owner: 'acme',
        repo: 'widgets',
        pullNumber: 42,
        baseRef: 'origin/main'
    });
    return { context, listFiles };
}

describe('ApiGuardrailContext.changedFiles', () => {
    it('pages with the routing params until a short page, mapping each file', async () => {
        const page1 = Array.from({ length: 100 }, (_, i) => makeFile(`f${i}.ts`));
        const page2 = [makeFile('src/a.ts', { additions: 5, deletions: 2, patch: '@@ -1 +1 @@' })];
        const { context, listFiles } = contextOver([page1, page2]);

        const files = await context.changedFiles();

        expect(files).toHaveLength(101);
        expect(files[100]).toEqual({
            path: 'src/a.ts',
            additions: 5,
            deletions: 2,
            patch: '@@ -1 +1 @@'
        });
        expect(listFiles).toHaveBeenCalledTimes(2);
        expect(listFiles.mock.calls[0]![0]).toEqual({
            owner: 'acme',
            repo: 'widgets',
            pull_number: 42,
            per_page: 100,
            page: 1
        });
        expect(listFiles.mock.calls[1]![0]!.page).toBe(2);
    });

    it('caps at 3000 files and stops paging once the cap is reached', async () => {
        // 31 full pages are available, but the loop must never request page 31:
        // after 30 pages of 100 the cap is hit and paging stops.
        const fullPages = Array.from({ length: 31 }, (_, p) =>
            Array.from({ length: 100 }, (_, i) => makeFile(`p${p}-f${i}.ts`))
        );
        const { context, listFiles } = contextOver(fullPages);

        const files = await context.changedFiles();

        expect(files).toHaveLength(3000);
        expect(listFiles).toHaveBeenCalledTimes(30);
    });

    it('memoizes: a second call pages the API no further', async () => {
        const { context, listFiles } = contextOver([[makeFile('a.ts')]]);

        await context.changedFiles();
        await context.changedFiles();

        expect(listFiles).toHaveBeenCalledTimes(1);
    });
});

describe('toChangedFile', () => {
    it('omits the patch field entirely when the API returned none (binary/large)', () => {
        const result = toChangedFile({ filename: 'logo.png', additions: 0, deletions: 0 });
        expect(result).toEqual({ path: 'logo.png', additions: 0, deletions: 0 });
        expect('patch' in result).toBe(false);
    });

    it('preserves an empty patch, distinguishing it from an absent one', () => {
        expect(toChangedFile({ filename: 'a.ts', additions: 0, deletions: 0, patch: '' })).toEqual({
            path: 'a.ts',
            additions: 0,
            deletions: 0,
            patch: ''
        });
    });
});
