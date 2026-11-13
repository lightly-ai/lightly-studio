import { describe, expect, it } from 'vitest';
import { buildGridFilter } from './buildGridFilter';

describe('buildGridFilter', () => {
    it('sets only the filter type when empty', () => {
        expect(buildGridFilter('image', {}, undefined)).toStrictEqual({ filter_type: 'image' });
    });

    it('omits undefined fields but keeps null and {}', () => {
        expect(
            buildGridFilter('video_frame', { frame_number: {}, video_id: undefined }, undefined)
        ).toStrictEqual({ filter_type: 'video_frame', frame_number: {} });
        expect(buildGridFilter('video_frame', { video_id: null }, undefined)).toStrictEqual({
            filter_type: 'video_frame',
            video_id: null
        });
    });

    it('adds sample_filter only when defined', () => {
        expect(buildGridFilter('image', {}, { tag_ids: ['t'] })).toStrictEqual({
            filter_type: 'image',
            sample_filter: { tag_ids: ['t'] }
        });
    });

    it('ignores reserved keys passed in fields', () => {
        const fields = { width: {}, filter_type: 'video', sample_filter: { tag_ids: ['old'] } };
        expect(buildGridFilter('image', fields, undefined)).toStrictEqual({
            filter_type: 'image',
            width: {}
        });
    });
});
