import { get } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { useHoveredSample } from './useHoveredSample';

describe('useHoveredSample', () => {
    it('sets the hovered sample and clears it only for the same sample', () => {
        const { hoveredSampleId, setHoveredSampleId, clearHoveredSampleId } = useHoveredSample();

        setHoveredSampleId('a');
        setHoveredSampleId('b');
        clearHoveredSampleId('a');
        expect(get(hoveredSampleId)).toBe('b');

        clearHoveredSampleId('b');
        expect(get(hoveredSampleId)).toBeNull();
    });
});
