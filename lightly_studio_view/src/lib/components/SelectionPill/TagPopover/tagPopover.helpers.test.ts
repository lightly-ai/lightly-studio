import { describe, expect, it } from 'vitest';
import { tagRowActions } from './tagPopover.helpers';

describe('tagRowActions', () => {
    it.each([
        [0, 3, { canAdd: true, canRemove: false }],
        [1, 3, { canAdd: true, canRemove: true }],
        [3, 3, { canAdd: false, canRemove: true }]
    ])('count %i of %i', (count, total, expected) => {
        expect(tagRowActions(count, total)).toEqual(expected);
    });
});
