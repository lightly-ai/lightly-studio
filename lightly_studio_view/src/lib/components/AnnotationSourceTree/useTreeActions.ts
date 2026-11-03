import { get } from 'svelte/store';
import { tickPairs, untickPairs } from '$lib/hooks/useAnnotationPairFilter/pairFilter.helpers';
import type { useAnnotationPairFilter } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';
import { toNamedPair, type PairRow } from './pairRows';
import { applyStatusAction, type StatusAction } from './treeStatus';

interface TreeActionsParams {
    getFilter: () => ReturnType<typeof useAnnotationPairFilter>;
    getRows: () => PairRow[];
    getMatches: () => PairRow[];
    /** Whether the tree has a "No annotations" row. */
    hasUnannotatedRow: () => boolean;
}

/** The tick changes the tree offers: status actions, group and row ticks, and "Only". */
export function useTreeActions({
    getFilter,
    getRows,
    getMatches,
    hasUnannotatedRow
}: TreeActionsParams) {
    const apply = (next: ReturnType<typeof applyStatusAction>) => {
        const filter = getFilter();
        filter.setUnticked(next.unticked);
        if (next.unannotatedTicked !== undefined && hasUnannotatedRow()) {
            filter.setUnannotatedTicked(next.unannotatedTicked);
        }
    };
    const run = (action: StatusAction, matches: PairRow[]) =>
        apply(
            applyStatusAction(action, {
                rows: getRows(),
                matches,
                unticked: get(getFilter().unticked)
            })
        );

    return {
        runStatusAction: (action: StatusAction) => run(action, getMatches()),
        setRows: (rows: PairRow[], ticked: boolean) => {
            const filter = getFilter();
            const pairs = rows.map(toNamedPair);
            const unticked = get(filter.unticked);
            filter.setUnticked(ticked ? tickPairs(unticked, pairs) : untickPairs(unticked, pairs));
        },
        onlyRows: (rows: PairRow[]) => run('showOnly', rows),
        onlyUnannotated: () =>
            apply({ unticked: getRows().map(toNamedPair), unannotatedTicked: true })
    };
}
