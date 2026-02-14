type RangeSelectionParams = {
    sampleIdsInOrder: string[];
    selectedSampleIds: Set<string>;
    clickedSampleId: string;
    clickedIndex: number;
    shiftKey: boolean;
    anchorSampleId: string | null;
    onSelectSample: (sampleId: string) => void;
};

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
