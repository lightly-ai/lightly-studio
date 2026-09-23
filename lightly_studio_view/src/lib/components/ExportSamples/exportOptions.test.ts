import { describe, expect, it } from 'vitest';
import { getDefaultExportType, getExportOptions } from './exportOptions';

describe('export options', () => {
    it('offers classifications and YouTube-VIS for videos', () => {
        expect(getExportOptions('video')).toEqual([
            { value: 'classifications', label: 'Video Classifications (CSV)' },
            {
                value: 'youtube_vis_segmentation',
                label: 'YouTube-VIS Video Segmentation Masks'
            }
        ]);
    });

    it('keeps YouTube-VIS as the video default', () => {
        expect(getDefaultExportType('video')).toBe('youtube_vis_segmentation');
    });

    it('does not offer whole-video classifications for video frames', () => {
        expect(getExportOptions('video_frame')).toEqual([
            {
                value: 'youtube_vis_segmentation',
                label: 'YouTube-VIS Video Segmentation Masks'
            }
        ]);
    });
});
