interface SelectCollectionLabelIdsParams {
    selectedLabelIds: string[];
    /** The label ids of the shown collection, or undefined while they load. */
    collectionLabelIds: string[] | undefined;
}

/**
 * Keeps the selected labels that the shown collection has. The label selection is kept across
 * collections, and a label of another dataset would match no sequence.
 */
export const selectCollectionLabelIds = ({
    selectedLabelIds,
    collectionLabelIds
}: SelectCollectionLabelIdsParams): string[] => {
    if (!collectionLabelIds) {
        return selectedLabelIds;
    }
    const collectionLabelIdSet = new Set(collectionLabelIds);
    return selectedLabelIds.filter((labelId) => collectionLabelIdSet.has(labelId));
};
