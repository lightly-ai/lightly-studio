import { describe, expect, it } from 'vitest';
import type { SampleView } from '$lib/api/lightly_studio_local';

import { findParentSampleIndexForCaption } from './findParentSampleIndexForCaption';

function makeSample(
    sampleId: string,
    captionIds: string[] = []
): SampleView {
    return {
        sample_id: sampleId,
        captions: captionIds.map((captionId) => ({
            sample_id: captionId,
            parent_sample_id: sampleId,
            text: 'caption'
        }))
    } as SampleView;
}

describe('findParentSampleIndexForCaption', () => {
    it('returns the parent row index for a nested caption id', () => {
        const items = [
            makeSample('parent-a', ['cap-a1']),
            makeSample('parent-b', ['cap-b1', 'cap-b2']),
            makeSample('parent-c', ['cap-c1'])
        ];

        expect(findParentSampleIndexForCaption(items, 'cap-b2')).toBe(1);
    });

    it('returns -1 when the caption is not loaded', () => {
        const items = [makeSample('parent-a', ['cap-a1'])];
        expect(findParentSampleIndexForCaption(items, 'missing')).toBe(-1);
    });
});
