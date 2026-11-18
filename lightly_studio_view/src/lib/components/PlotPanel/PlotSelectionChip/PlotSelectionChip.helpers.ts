export type PickHint = 'pick' | 'add' | 'remove';

interface GetPickHintParams {
    hoveredSampleId: string | null;
    pickedSampleIds: readonly string[];
}

// What a Shift + click on the hovered point does. A Shift + click on a region replaces it with
// one pick, so only existing picks turn the verb into add or remove.
export function getPickHint({
    hoveredSampleId,
    pickedSampleIds
}: GetPickHintParams): PickHint | null {
    if (hoveredSampleId === null) return null;
    if (pickedSampleIds.length === 0) return 'pick';
    return pickedSampleIds.includes(hoveredSampleId) ? 'remove' : 'add';
}
