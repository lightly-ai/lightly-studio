import type { SourceLabelPair } from '$lib/api/lightly_studio_local';

/** A pair with its class name, so overlays can match annotations that carry only the name. */
export type NamedPair = SourceLabelPair & { label_name: string };

export interface PairFilterState {
    /** The pairs the user unticked. Everything else, also pairs added later, is ticked. */
    unticked: NamedPair[];
    unannotatedTicked: boolean;
    /** Every pair of the collection, as last reported by the tree. */
    known: NamedPair[];
}

export const DEFAULT_PAIR_FILTER_STATE: PairFilterState = {
    unticked: [],
    unannotatedTicked: true,
    known: []
};

// Matches no annotation. Sent when the user unticks every pair, because an empty list reads
// as "no filter".
const NIL_ID = '00000000-0000-0000-0000-000000000000';
export const NO_MATCH_PAIR: SourceLabelPair = {
    collection_id: NIL_ID,
    annotation_label_id: NIL_ID
};

export const isSamePair = (a: SourceLabelPair, b: SourceLabelPair) =>
    a.collection_id === b.collection_id && a.annotation_label_id === b.annotation_label_id;

export const isSamePairList = (a: SourceLabelPair[], b: SourceLabelPair[]) =>
    a.length === b.length && a.every((pair, index) => isSamePair(pair, b[index]));

const includesPair = (list: SourceLabelPair[], pair: SourceLabelPair) =>
    list.some((item) => isSamePair(item, pair));

export const isPairTicked = (unticked: SourceLabelPair[], pair: SourceLabelPair) =>
    !includesPair(unticked, pair);

/** Ticks `pairs`: the new unticked list. */
export const tickPairs = (unticked: NamedPair[], pairs: SourceLabelPair[]) =>
    unticked.filter((item) => !includesPair(pairs, item));

/** Unticks `pairs`: the new unticked list. */
export const untickPairs = (unticked: NamedPair[], pairs: NamedPair[]) => [
    ...unticked,
    ...pairs.filter((pair) => !includesPair(unticked, pair))
];

/** Ticks only `pairs` out of `all`: the new unticked list. */
export const tickOnlyPairs = (all: NamedPair[], pairs: SourceLabelPair[]) =>
    all.filter((pair) => !includesPair(pairs, pair));

const toRequestPair = ({ collection_id, annotation_label_id }: SourceLabelPair) => ({
    collection_id,
    annotation_label_id
});

/** Whether anything is unticked, i.e. the grid is filtered. */
export const isFilterActive = (state: PairFilterState) =>
    !state.unannotatedTicked || state.known.some((pair) => includesPair(state.unticked, pair));

/**
 * The request for the grid. Everything ticked sends nothing. Otherwise the ticked pairs, and
 * the unannotated images when "No annotations" is ticked.
 */
export const toPairRequest = (
    state: PairFilterState
): { pairs: SourceLabelPair[]; includeUnannotated: boolean } => {
    if (!isFilterActive(state)) return { pairs: [], includeUnannotated: false };
    const ticked = state.known
        .filter((pair) => isPairTicked(state.unticked, pair))
        .map(toRequestPair);
    return {
        pairs: ticked.length > 0 ? ticked : [NO_MATCH_PAIR],
        includeUnannotated: state.unannotatedTicked
    };
};
