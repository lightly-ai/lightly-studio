import type { useAnnotationTreeState } from '$lib/hooks/useAnnotationTreeState/useAnnotationTreeState';
import type { PairKey } from './pairRows';
import { leafTargets, type TreeLeaf } from './treeBranches';

type TreeState = ReturnType<typeof useAnnotationTreeState>;

interface TreeScope {
    allPairs: PairKey[];
    sourceIds: string[];
}

/**
 * Tick and eye actions on tree rows. A row ticks its pairs and its "No annotations" sources,
 * and its eye shows or hides its pairs.
 */
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
        setVisible: (leaves: TreeLeaf[], visible: boolean) =>
            getTree().setVisible(leafTargets(leaves).pairs, visible),
        only: (leaves: TreeLeaf[]) => {
            const { pairs, unannotatedIds } = leafTargets(leaves);
            onlyTargets(pairs, unannotatedIds);
        },
        onlyTargets
    };
};
