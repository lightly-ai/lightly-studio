import { describe, expect, it } from 'vitest';
import { SampleType } from '$lib/api/lightly_studio_local';
import { getSourceOwnerLabel } from './getSourceOwnerLabel';

describe('getSourceOwnerLabel', () => {
    it.each([
        [SampleType.IMAGE, 'Images'],
        [SampleType.VIDEO, 'Videos'],
        [SampleType.VIDEO_FRAME, 'Frames'],
        [SampleType.GROUP, 'Groups'],
        [SampleType.SEQUENCE, 'Point clouds']
    ])('names a %s collection %s', (sampleType, label) => {
        expect(getSourceOwnerLabel({ parent_sample_type: sampleType })).toBe(label);
    });

    it('names a group component by its component name', () => {
        expect(
            getSourceOwnerLabel({
                parent_sample_type: SampleType.IMAGE,
                parent_group_component_name: 'front'
            })
        ).toBe('front');
    });

    it('falls back to the sample type for an empty component name', () => {
        expect(
            getSourceOwnerLabel({
                parent_sample_type: SampleType.VIDEO_FRAME,
                parent_group_component_name: ''
            })
        ).toBe('Frames');
    });

    it('falls back to the raw sample type when the menu has no word for it', () => {
        expect(getSourceOwnerLabel({ parent_sample_type: SampleType.MCAP })).toBe('mcap');
    });
});
