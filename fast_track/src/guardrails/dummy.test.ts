import { describe, expect, it } from 'vitest';

import { dummyGuardrail } from './dummy';

describe('dummyGuardrail', () => {
    it('always passes', async () => {
        const result = await dummyGuardrail.run({
            changedFiles: async () => []
        });
        expect(result).toEqual({ status: 'pass', summary: 'Always passes.' });
    });
});
