type TagCheckState = 'checked' | 'indeterminate' | 'unchecked';

interface ComputeTagStatesParams {
    /** Tag ids of every target whose tags are loaded, one entry per target. */
    tagIdsPerKnownTarget: string[][];
    allTagIds: string[];
}

/**
 * Derives the tri-state checkbox state of every tag for the current target set.
 *
 * Targets whose tags are not loaded (a select-all resolved by filter) are simply
 * absent from `tagIdsPerKnownTarget`: the state describes the known targets, while
 * mutations still apply to the full target set. Callers should surface that gap in
 * the UI rather than fetching the missing tags.
 *
 * @param params The per-target tag ids and every tag to report on.
 * @returns A state per tag id; tags no target has are `unchecked`.
 */
export function computeTagStates({
    tagIdsPerKnownTarget,
    allTagIds
}: ComputeTagStatesParams): Record<string, TagCheckState> {
    const states: Record<string, TagCheckState> = {};
    const knownCount = tagIdsPerKnownTarget.length;

    for (const tagId of allTagIds) {
        const hits = tagIdsPerKnownTarget.filter((tagIds) => tagIds.includes(tagId)).length;
        if (hits === 0 || knownCount === 0) {
            states[tagId] = 'unchecked';
        } else if (hits === knownCount) {
            states[tagId] = 'checked';
        } else {
            states[tagId] = 'indeterminate';
        }
    }

    return states;
}
