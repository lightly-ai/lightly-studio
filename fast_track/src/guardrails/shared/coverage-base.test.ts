import { describe, expect, it, vi } from 'vitest';
import type { ChangedFile, GuardrailContext } from '../context/types';
import { createCoverageGuardrail } from './coverage-base';

// Minimal patch that adds lines 1–3.
const PATCH = '@@ -0,0 +1,3 @@\n+line 1\n+line 2\n+line 3\n';

type FakeCoverage = Record<string, never>;

function makeConfig(
    overrides: Partial<{
        filterFiles(files: ChangedFile[]): ChangedFile[];
        findTestFile(path: string): Promise<string | undefined>;
        runTests(testFiles: string[], sourcePaths: string[]): Promise<FakeCoverage | null>;
        parseCoverageRatio(
            data: FakeCoverage,
            sourcePath: string,
            addedLines: Set<number>
        ): number | null;
    }> = {}
) {
    return {
        name: 'test/coverage',
        filterFiles: (files: ChangedFile[]) => files,
        findTestFile: async (): Promise<string | undefined> => 'tests/test_foo.py',
        runTests: async (): Promise<FakeCoverage | null> => ({}) as FakeCoverage,
        parseCoverageRatio: (): number | null => 1.0,
        ...overrides
    };
}

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

const FILE: ChangedFile = {
    path: 'src/lightly_studio/model.py',
    status: 'modified',
    additions: 3,
    deletions: 0,
    patch: PATCH
};

describe('createCoverageGuardrail', () => {
    it('is required and runs locally', () => {
        const g = createCoverageGuardrail(makeConfig());
        expect(g.required).toBe(true);
        expect(g.name).toBe('test/coverage');
    });

    it('passes immediately when filterFiles returns nothing', async () => {
        const g = createCoverageGuardrail(makeConfig({ filterFiles: () => [] }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('passes immediately when all filtered files are deleted', async () => {
        const deletedFile: ChangedFile = { ...FILE, status: 'deleted' };
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([deletedFile]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('passes immediately when all filtered files lack a patch', async () => {
        const noPatchFile: ChangedFile = {
            path: 'src/lightly_studio/model.py',
            status: 'modified',
            additions: 3,
            deletions: 0
        };
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([noPatchFile]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('does not call findTestFile for patch-less files', async () => {
        const noPatchFile: ChangedFile = {
            path: 'src/lightly_studio/model.py',
            status: 'modified',
            additions: 3,
            deletions: 0
        };
        const findTestFile = vi.fn<(path: string) => Promise<string | undefined>>(
            async () => 'tests/test_foo.py'
        );
        const g = createCoverageGuardrail(makeConfig({ findTestFile }));
        await g.run(makeCtx([noPatchFile]));
        expect(findTestFile).not.toHaveBeenCalled();
    });

    it('processes only files with a patch when mixed with patch-less files', async () => {
        const noPatchFile: ChangedFile = {
            path: 'src/lightly_studio/no_patch.py',
            status: 'modified',
            additions: 3,
            deletions: 0
        };
        const g = createCoverageGuardrail(makeConfig({ parseCoverageRatio: () => 0.8 }));
        const result = await g.run(makeCtx([noPatchFile, FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain(FILE.path);
        expect(result.summary).not.toContain('no_patch.py');
    });

    it('does not fail when a deletion-only patch file has no test file', async () => {
        const deletionOnlyFile: ChangedFile = {
            path: 'src/lightly_studio/deleted_lines.py',
            status: 'modified',
            additions: 0,
            deletions: 3,
            patch: '@@ -1,3 +1,0 @@\n-line 1\n-line 2\n-line 3\n'
        };
        const g = createCoverageGuardrail(
            makeConfig({
                findTestFile: async (p) =>
                    p.includes('deleted_lines') ? undefined : 'tests/test_foo.py'
            })
        );
        const result = await g.run(makeCtx([deletionOnlyFile, FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).not.toContain('no test file found');
    });

    it('fails when no test file is found', async () => {
        const g = createCoverageGuardrail(makeConfig({ findTestFile: async () => undefined }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('no test file found');
        expect(result.summary).toContain(FILE.path);
    });

    it('fails when runTests returns null', async () => {
        const g = createCoverageGuardrail(makeConfig({ runTests: async () => null }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('coverage data not found');
        expect(result.summary).toContain(FILE.path);
    });

    it('passes when parseCoverageRatio returns null (no executable added lines)', async () => {
        const g = createCoverageGuardrail(makeConfig({ parseCoverageRatio: () => null }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
    });

    it('passes when coverage meets the 80% threshold', async () => {
        const g = createCoverageGuardrail(makeConfig({ parseCoverageRatio: () => 0.8 }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('[PASS]');
        expect(result.summary).toContain(FILE.path);
    });

    it('fails when coverage is below the 80% threshold', async () => {
        const g = createCoverageGuardrail(makeConfig({ parseCoverageRatio: () => 0.75 }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('75.0%');
        expect(result.summary).toContain('80%');
        expect(result.summary).toContain(FILE.path);
    });

    it('batches all source files into a single runTests call', async () => {
        const runTests = vi.fn<
            (testFiles: string[], sourcePaths: string[]) => Promise<FakeCoverage>
        >(async () => ({}) as FakeCoverage);
        const file2: ChangedFile = {
            path: 'src/lightly_studio/service.py',
            status: 'modified',
            additions: 1,
            deletions: 0,
            patch: PATCH
        };
        const g = createCoverageGuardrail(makeConfig({ runTests }));
        await g.run(makeCtx([FILE, file2]));
        expect(runTests).toHaveBeenCalledTimes(1);
        expect(runTests.mock.calls[0]![1]).toHaveLength(2); // two source paths
    });

    it('deduplicates test files passed to runTests', async () => {
        const runTests = vi.fn<
            (testFiles: string[], sourcePaths: string[]) => Promise<FakeCoverage>
        >(async () => ({}) as FakeCoverage);
        const file2: ChangedFile = {
            path: 'src/lightly_studio/service.py',
            status: 'modified',
            additions: 1,
            deletions: 0,
            patch: PATCH
        };
        // Both files map to the same test file via the default findTestFile.
        const g = createCoverageGuardrail(makeConfig({ runTests }));
        await g.run(makeCtx([FILE, file2]));
        expect(runTests.mock.calls[0]![0]).toHaveLength(1); // deduplicated
    });

    it('collects failures from both missing test files and low coverage', async () => {
        const noTestFile: ChangedFile = {
            path: 'src/lightly_studio/no_test.py',
            status: 'modified',
            additions: 1,
            deletions: 0,
            patch: PATCH
        };
        const lowFile: ChangedFile = {
            path: 'src/lightly_studio/low.py',
            status: 'modified',
            additions: 1,
            deletions: 0,
            patch: PATCH
        };
        const g = createCoverageGuardrail(
            makeConfig({
                findTestFile: async (p) =>
                    p.includes('no_test') ? undefined : 'tests/test_low.py',
                parseCoverageRatio: () => 0.5
            })
        );
        const result = await g.run(makeCtx([noTestFile, lowFile]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('no_test.py');
        expect(result.summary).toContain('low.py');
    });
});
