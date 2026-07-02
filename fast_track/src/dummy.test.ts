import { describe, expect, it } from 'vitest';

import { dummy } from './dummy';

describe('dummy', () => {
    it('is a dummy', () => {
        expect(dummy).toBe(true);
    });
});
