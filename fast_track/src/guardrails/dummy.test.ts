import { describe, expect, it } from 'vitest';

import { dummyGuardrail } from './dummy';

describe('dummyGuardrail', () => {
    it('always passes', async () => {
        const result = await dummyGuardrail.run({
            baseRef: 'origin/main',
            changedFiles: async () => []
        });
        expect(result).toEqual({ status: 'pass', summary: 'Always passes.' });
    });
});
