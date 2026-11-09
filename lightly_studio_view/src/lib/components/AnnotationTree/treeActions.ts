import type { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import type { PairKey } from './pairRows';
import { leafTargets, type TreeLeaf } from './treeBranches';

type TreeState = ReturnType<typeof useAnnotationTreeState>;

interface TreeScope {
    allPairs: PairKey[];
    sourceIds: string[];
}

/** Tick actions on tree rows. A row ticks its pairs and its "No annotations" sources. */
export const createTreeActions = (getTree: () => TreeState, getScope: () => TreeScope) => {
    // Only the given "No annotations" rows stay ticked, so a source keeps its own.
    const onlyTargets = (pairs: PairKey[], unannotatedIds: string[]) => {
        const { allPairs, sourceIds } = getScope();
        const others = sourceIds.filter((id) => !unannotatedIds.includes(id));
        getTree().only(pairs, allPairs);
        getTree().setUnannotatedTicked(others, false);
        getTree().setUnannotatedTicked(unannotatedIds, true);
    };
    return {
        setTicked: (leaves: TreeLeaf[], ticked: boolean) => {
            const { pairs, unannotatedIds } = leafTargets(leaves);
            getTree().setTicked(pairs, ticked);
            getTree().setUnannotatedTicked(unannotatedIds, ticked);
        },
        only: (leaves: TreeLeaf[]) => {
            const { pairs, unannotatedIds } = leafTargets(leaves);
            onlyTargets(pairs, unannotatedIds);
        },
        onlyTargets
    };
};
