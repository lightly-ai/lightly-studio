import type { Query } from '@tanstack/svelte-query';

/**
 * Matches the getAnnotation queries of one annotation, whatever collection they were
 * fetched for. The side panel row and the box on the image read the class from them.
 */
export const isAnnotationQueryOf =
    (annotationId: string) =>
    (query: Pick<Query, 'queryKey'>): boolean => {
        const key = query.queryKey[0] as
            | { _id?: string; path?: { annotation_id?: string } }
            | undefined;
        return key?._id === 'getAnnotation' && key.path?.annotation_id === annotationId;
    };

/**
 * Picks black or white text for a fill color, whichever has the higher WCAG contrast.
 * Takes an `rgb()` or `rgba()` string, as returned by getColorByLabel.
 */
export const getReadableTextColor = (fill: string): 'black' | 'white' => {
    const [r, g, b] = (fill.match(/\d+(\.\d+)?/g) ?? []).slice(0, 3).map(Number);
    const luminance = 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
    // Contrast with black is (L + 0.05) / 0.05, with white 1.05 / (L + 0.05). They are
    // equal at L ≈ 0.179.
    return luminance > 0.179 ? 'black' : 'white';
};

const toLinear = (channel: number): number => {
    const value = channel / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
};
