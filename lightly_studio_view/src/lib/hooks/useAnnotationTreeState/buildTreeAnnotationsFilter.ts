import type { PairKey } from '$lib/components/AnnotationTree/pairRows';

const isSamePair = (a: PairKey, b: PairKey) =>
    a.collection_id === b.collection_id && a.annotation_label_id === b.annotation_label_id;

/**
 * Turns the tree's unticked state into the grid's annotation filter.
 * Stale unticked entries (no longer in the tree) are ignored. Returns undefined when nothing is
 * unticked, so the grid can skip the filter.
 */
export const buildTreeAnnotationsFilter = (
    allPairs: PairKey[],
    untickedPairs: PairKey[],
    untickedUnannotated: string[],
    sourceIds: string[]
): { annotation_pairs?: PairKey[]; unannotated_collection_ids?: string[] } | undefined => {
    const isUnticked = (pair: PairKey) => untickedPairs.some((other) => isSamePair(other, pair));
    const isUnannotatedUnticked = (id: string) => untickedUnannotated.includes(id);

    const hasUntickedPair = allPairs.some(isUnticked);
    const hasUntickedSource = sourceIds.some(isUnannotatedUnticked);
    if (!hasUntickedPair && !hasUntickedSource) return undefined;

    return {
        annotation_pairs: allPairs.filter((pair) => !isUnticked(pair)),
        unannotated_collection_ids: sourceIds.filter((id) => !isUnannotatedUnticked(id))
    };
};
