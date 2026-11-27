import { describe, expect, it } from 'vitest';
import { resolveEgoPosition } from './resolveEgoPosition';

describe('resolveEgoPosition', () => {
    it('returns the loaded position', () => {
        expect(resolveEgoPosition({ canQuery: true, isError: false, position: [1, 2, 0] })).toEqual(
            [1, 2, 0]
        );
    });

    it('treats a failed request as an unknown position', () => {
        expect(
            resolveEgoPosition({ canQuery: true, isError: true, position: undefined })
        ).toBeNull();
    });

    it('returns undefined while the position loads', () => {
        expect(
            resolveEgoPosition({ canQuery: true, isError: false, position: undefined })
        ).toBeUndefined();
    });

    it('returns undefined when the position is not requested', () => {
        expect(
            resolveEgoPosition({ canQuery: false, isError: false, position: [1, 2, 0] })
        ).toBeUndefined();
    });
});
