import { describe, expect, it } from 'vitest';
import type { CaptionView } from '$lib/api/lightly_studio_local';
import {
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY
} from '$lib/constants';
import {
    getCaptionRepeatGroupId,
    getCaptionRepeatMaxSimilarity,
    getRepeatGroupColors,
    hasRepeatedCaptionGroups
} from './captionRepetition';

function makeCaption(overrides: {
    sample_id?: string;
    groupId?: number;
    maxSim?: number;
}): CaptionView {
    const data: Record<string, number> = {};
    if (overrides.groupId !== undefined) {
        data[REPEATED_CAPTION_GROUP_ID_KEY] = overrides.groupId;
    }
    if (overrides.maxSim !== undefined) {
        data[REPEATED_CAPTION_MAX_SIMILARITY_KEY] = overrides.maxSim;
    }
    return {
        sample_id: overrides.sample_id ?? 'cap-1',
        parent_sample_id: 'sample-1',
        text: 'Caption',
        metadata_dict: { data }
    } as CaptionView;
}

describe('captionRepetition', () => {
    it('reads group id and max similarity from metadata', () => {
        const caption = makeCaption({ groupId: 2, maxSim: 0.91 });
        expect(getCaptionRepeatGroupId(caption.metadata_dict)).toBe(2);
        expect(getCaptionRepeatMaxSimilarity(caption.metadata_dict)).toBe(0.91);
    });

    it('returns null when metadata keys are missing', () => {
        expect(getCaptionRepeatGroupId({ data: {} })).toBeNull();
        expect(getCaptionRepeatMaxSimilarity(null)).toBeNull();
    });

    it('detects whether any caption has a repeat group', () => {
        expect(hasRepeatedCaptionGroups([makeCaption({})])).toBe(false);
        expect(hasRepeatedCaptionGroups([makeCaption({ groupId: 0 })])).toBe(true);
    });

    it('returns stable rgba colors for a group id', () => {
        const a = getRepeatGroupColors(0);
        const b = getRepeatGroupColors(0);
        const c = getRepeatGroupColors(1);
        expect(a.color).toBe(b.color);
        expect(a.color).toMatch(/^rgba\(/);
        expect(a.color).not.toBe(c.color);
    });
});
