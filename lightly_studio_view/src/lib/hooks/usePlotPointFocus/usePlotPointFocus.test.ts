import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';

import { usePlotPointFocus } from './usePlotPointFocus';

describe('usePlotPointFocus', () => {
    it('stores focused sample ids per collection', () => {
        const captions = usePlotPointFocus('captions-collection');
        const images = usePlotPointFocus('images-collection');

        captions.setFocusedPlotSampleId('caption-1');
        images.setFocusedPlotSampleId('image-1');

        expect(get(captions.focusedPlotSampleId)).toBe('caption-1');
        expect(get(images.focusedPlotSampleId)).toBe('image-1');
    });

    it('clears focus for a collection', () => {
        const captions = usePlotPointFocus('captions-clear');
        captions.setFocusedPlotSampleId('caption-1');
        captions.setFocusedPlotSampleId(null);

        expect(get(captions.focusedPlotSampleId)).toBeNull();
    });
});
