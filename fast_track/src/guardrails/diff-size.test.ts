import { describe, expect, it } from 'vitest';
import type { ChangedFile, GuardrailContext } from './context/types';
import { diffSizeGuardrail, isExcluded, MAX_ADDED_LOC } from './diff-size';

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

describe('diffSizeGuardrail', () => {
    it('is required and runs locally', () => {
        expect(diffSizeGuardrail.required).toBe(true);
        expect(diffSizeGuardrail.needsPrContext).toBe(false);
    });

    it('passes when total additions are below the limit', async () => {
        const result = await diffSizeGuardrail.run(
            makeCtx([
                { path: 'a.py', status: 'modified', additions: 100, deletions: 0 },
                { path: 'b.py', status: 'modified', additions: 50, deletions: 5 }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('150');
    });

    it('passes when total additions are exactly the limit', async () => {
        const result = await diffSizeGuardrail.run(
            makeCtx([{ path: 'a.py', status: 'modified', additions: MAX_ADDED_LOC, deletions: 0 }])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`${MAX_ADDED_LOC}`);
    });

    it('fails when total additions exceed the limit', async () => {
        const result = await diffSizeGuardrail.run(
            makeCtx([
                { path: 'a.py', status: 'modified', additions: 200, deletions: 0 },
                { path: 'b.py', status: 'added', additions: 50, deletions: 0 }
            ])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('250');
        expect(result.summary).toContain(`${MAX_ADDED_LOC}`);
    });

    it('ignores generated lock files even when their additions would exceed the limit', async () => {
        const result = await diffSizeGuardrail.run(
            makeCtx([
                { path: 'a.py', status: 'modified', additions: 10, deletions: 0 },
                {
                    path: 'lightly_studio/uv.lock',
                    status: 'modified',
                    additions: 5000,
                    deletions: 0
                },
                {
                    path: 'lightly_studio_view/package-lock.json',
                    status: 'modified',
                    additions: 3000,
                    deletions: 0
                },
                {
                    path: 'fast_track/package-lock.json',
                    status: 'modified',
                    additions: 2000,
                    deletions: 0
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('10');
    });

    it('ignores files under excluded directory prefixes', async () => {
        const result = await diffSizeGuardrail.run(
            makeCtx([
                { path: 'a.py', status: 'modified', additions: 10, deletions: 0 },
                {
                    path: 'lightly_studio/tests/benchmarks/bench_foo.py',
                    status: 'added',
                    additions: 500,
                    deletions: 0
                },
                {
                    path: 'lightly_studio/src/lightly_studio/vendor/some_lib.py',
                    status: 'added',
                    additions: 1000,
                    deletions: 0
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('10');
    });
});

describe('isExcluded', () => {
    it('matches exact lock file paths', () => {
        expect(isExcluded('lightly_studio/uv.lock')).toBe(true);
        expect(isExcluded('lightly_studio_view/package-lock.json')).toBe(true);
        expect(isExcluded('fast_track/package-lock.json')).toBe(true);
    });

    it('matches files under excluded directory prefixes', () => {
        expect(isExcluded('lightly_studio/tests/benchmarks/bench_foo.py')).toBe(true);
        expect(isExcluded('lightly_studio/src/lightly_studio/vendor/lib.py')).toBe(true);
    });

    it('does not match unrelated paths', () => {
        expect(isExcluded('lightly_studio/src/main.py')).toBe(false);
        expect(isExcluded('fast_track/src/index.ts')).toBe(false);
    });

    it('does not match a path that only shares a prefix with an excluded directory', () => {
        expect(isExcluded('lightly_studio/tests/benchmarks_extra/file.py')).toBe(false);
    });
});
