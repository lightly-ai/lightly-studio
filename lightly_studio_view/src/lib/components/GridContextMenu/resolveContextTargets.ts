interface ResolveContextTargetsParams {
    clickedId: string;
    selectedSampleIds: Set<string>;
}

interface ResolveContextTargetsReturn {
    ids: string[];
    /** True when the menu acts on the multi-selection instead of the clicked sample alone. */
    isSelectionTarget: boolean;
}

/**
 * Decides which samples a context menu opened on `clickedId` should act on.
 *
 * Right-clicking inside the selection targets the whole selection; right-clicking
 * outside it targets only the clicked sample and leaves the selection untouched.
 *
 * @param params The clicked sample and the current selection.
 * @returns The target ids and whether they came from the selection.
 */
export function resolveContextTargets({
    clickedId,
    selectedSampleIds
}: ResolveContextTargetsParams): ResolveContextTargetsReturn {
    if (selectedSampleIds.has(clickedId)) {
        return { ids: [...selectedSampleIds], isSelectionTarget: true };
    }
    return { ids: [clickedId], isSelectionTarget: false };
}
