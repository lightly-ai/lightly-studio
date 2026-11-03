import { describe, expect, it } from 'vitest';
import { DEFAULT_SOURCE_NAME, resolveTargetSource } from './resolveTargetSource';

describe('resolveTargetSource', () => {
    it('uses the chosen source, also one that does not exist yet', () => {
        expect(resolveTargetSource('new_source', ['ground_truth', 'predictions'])).toBe(
            'new_source'
        );
    });

    it('uses the only source', () => {
        expect(resolveTargetSource(null, ['ground_truth'])).toBe('ground_truth');
    });

    it('uses the backend default when there is no source', () => {
        expect(resolveTargetSource(undefined, [])).toBe(DEFAULT_SOURCE_NAME);
    });

    it('picks nothing when there are several sources', () => {
        expect(resolveTargetSource(null, ['ground_truth', 'predictions'])).toBeNull();
    });
});
