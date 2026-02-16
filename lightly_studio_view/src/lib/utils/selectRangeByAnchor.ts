type RangeSelectionParams = {
    sampleIdsInOrder: string[];
    selectedSampleIds: Set<string>;
    clickedSampleId: string;
    clickedIndex: number;
    shiftKey: boolean;
    anchorSampleId: string | null;
    onSelectSample: (sampleId: string) => void;
};

/**
 * Selects one item or a Shift range, then returns the anchor for the next click.
 *
 * Regular click:
 * - selects only the clicked item (via `onSelectSample`)
 * - sets the clicked item as new anchor
 *
 * Shift+click with valid anchor:
 * - selects all unselected items between anchor and clicked index (inclusive)
 * - keeps the existing anchor
 *
 * Shift+click without valid anchor behaves like a regular click.
 *
 * @param params Full selection context for the current interaction.
 * @returns The anchor id to store for the next interaction.
 */
export function selectRangeByAnchor({
    sampleIdsInOrder,
    selectedSampleIds,
    clickedSampleId,
    clickedIndex,
    shiftKey,
    anchorSampleId,
    onSelectSample
}: RangeSelectionParams): string | null {
    const anchorIndex = anchorSampleId ? sampleIdsInOrder.indexOf(anchorSampleId) : -1;

    if (shiftKey && anchorIndex >= 0) {
        const rangeStart = Math.min(anchorIndex, clickedIndex);
        const rangeEnd = Math.max(anchorIndex, clickedIndex);

        for (let index = rangeStart; index <= rangeEnd; index++) {
            const sampleId = sampleIdsInOrder[index];
            if (sampleId && !selectedSampleIds.has(sampleId)) {
                onSelectSample(sampleId);
            }
        }
        return anchorSampleId;
    }

    onSelectSample(clickedSampleId);
    return clickedSampleId;
}
