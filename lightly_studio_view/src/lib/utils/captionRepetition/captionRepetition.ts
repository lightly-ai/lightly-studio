import type { CaptionView } from '$lib/api/lightly_studio_local';
import {
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY
} from '$lib/constants';
import { getColorPair } from '$lib/utils/getColorPair';
import { oklchHueWheelColor } from '$lib/utils/colorConvert';

const REPEAT_GROUP_PALETTE_SIZE = 12;
const REPEAT_GROUP_FILL_ALPHA = 0.7;

/**
 * Reads `repeated_caption_group_id` from caption metadata, if present.
 */
export function getCaptionRepeatGroupId(
    metadataDict: CaptionView['metadata_dict']
): number | null {
    const value = metadataDict?.data?.[REPEATED_CAPTION_GROUP_ID_KEY];
    return typeof value === 'number' ? value : null;
}

/**
 * Reads `repeated_caption_max_similarity` from caption metadata, if present.
 */
export function getCaptionRepeatMaxSimilarity(
    metadataDict: CaptionView['metadata_dict']
): number | null {
    const value = metadataDict?.data?.[REPEATED_CAPTION_MAX_SIMILARITY_KEY];
    return typeof value === 'number' ? value : null;
}

/** True when any caption belongs to a repetition group. */
export function hasRepeatedCaptionGroups(captions: CaptionView[]): boolean {
    return captions.some(
        (caption) => getCaptionRepeatGroupId(caption.metadata_dict) !== null
    );
}

/**
 * Stable fill + contrast colors for a repetition group id (hue wheel).
 */
export function getRepeatGroupColors(groupId: number): {
    color: string;
    contrastColor: string;
} {
    const index =
        ((groupId % REPEAT_GROUP_PALETTE_SIZE) + REPEAT_GROUP_PALETTE_SIZE) %
        REPEAT_GROUP_PALETTE_SIZE;
    const rgb = oklchHueWheelColor({
        index,
        count: REPEAT_GROUP_PALETTE_SIZE,
        lightness: 0.65,
        chroma: 0.2
    });
    return getColorPair(rgb, REPEAT_GROUP_FILL_ALPHA);
}
