import { describe, expect, it } from 'vitest';
import { computeTagStates } from './computeTagStates';

describe('computeTagStates', () => {
    it('marks a tag checked only when every known target has it', () => {
        const states = computeTagStates({
            tagIdsPerKnownTarget: [['train', 'reviewed'], ['train']],
            allTagIds: ['train', 'reviewed', 'blurry']
        });

        expect(states).toEqual({
            train: 'checked',
            reviewed: 'indeterminate',
            blurry: 'unchecked'
        });
    });

    it('reports a single target as checked or unchecked, never indeterminate', () => {
        const states = computeTagStates({
            tagIdsPerKnownTarget: [['train']],
            allTagIds: ['train', 'blurry']
        });

        expect(states).toEqual({ train: 'checked', blurry: 'unchecked' });
    });

    it('ignores targets whose tags are not loaded', () => {
        // Two of three targets are loaded; the third contributes no entry.
        const states = computeTagStates({
            tagIdsPerKnownTarget: [['train'], ['train']],
            allTagIds: ['train']
        });

        expect(states).toEqual({ train: 'checked' });
    });

    it('marks everything unchecked when no target tags are known', () => {
        const states = computeTagStates({
            tagIdsPerKnownTarget: [],
            allTagIds: ['train', 'blurry']
        });

        expect(states).toEqual({ train: 'unchecked', blurry: 'unchecked' });
    });
});
