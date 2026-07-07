import { describe, expect, it } from 'vitest';
import type { ChangedFile, GuardrailContext } from './context/types';
import { diffSizeGuardrail, MAX_ADDED_LOC } from './diff-size';

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
});
