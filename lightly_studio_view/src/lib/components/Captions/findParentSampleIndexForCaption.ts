import type { SampleView } from '$lib/api/lightly_studio_local';

/**
 * Finds the captions-grid row whose nested captions include the given caption sample id.
 * Plot points use caption sample ids; grid rows are parent samples.
 */
export function findParentSampleIndexForCaption(
    items: SampleView[],
    captionSampleId: string
): number {
    return items.findIndex((item) =>
        item.captions?.some((caption) => caption.sample_id === captionSampleId)
    );
}
