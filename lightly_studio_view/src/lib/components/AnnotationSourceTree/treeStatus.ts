import {
    tickOnlyPairs,
    tickPairs,
    untickPairs,
    type NamedPair
} from '$lib/hooks/useAnnotationPairFilter/pairFilter.helpers';
import { toNamedPair, type PairRow } from './pairRows';

export type StatusAction = 'showOnly' | 'add' | 'hide' | 'showAll' | 'hideAll';

export const STATUS_ACTION_LABELS: Record<StatusAction, string> = {
    showOnly: 'Show only',
    add: 'Add',
    hide: 'Hide',
    showAll: 'Show all',
    hideAll: 'Hide all'
};

interface TreeStatusParams {
    rows: PairRow[];
    matches: PairRow[];
    searching: boolean;
    /** Whether "No annotations" is ticked. Undefined when the row does not exist. */
    unannotatedTicked?: boolean;
}

/** The status line under the search: what is shown, and the actions that change something. */
export const getTreeStatus = ({
    rows,
    matches,
    searching,
    unannotatedTicked
}: TreeStatusParams): { text: string; actions: StatusAction[] } => {
    if (searching) return getSearchStatus(rows, matches, unannotatedTicked);
    const hasRow = unannotatedTicked !== undefined;
    const total = rows.length + (hasRow ? 1 : 0);
    const shown = rows.filter((row) => row.ticked).length + (unannotatedTicked ? 1 : 0);
    if (shown === total) return { text: 'Showing everything', actions: [] };
    if (shown === 0) return { text: 'Everything hidden', actions: ['showAll'] };
    return { text: `${total - shown} hidden`, actions: ['showAll', 'hideAll'] };
};

const getSearchStatus = (
    rows: PairRow[],
    matches: PairRow[],
    unannotatedTicked?: boolean
): { text: string; actions: StatusAction[] } => {
    if (matches.length === 0) return { text: 'No matches', actions: [] };
    const shown = matches.filter((row) => row.ticked).length;
    const someOtherTicked =
        Boolean(unannotatedTicked) || rows.some((row) => row.ticked && !matches.includes(row));
    const actions: StatusAction[] = [];
    if (someOtherTicked || shown < matches.length) actions.push('showOnly');
    if (shown < matches.length) actions.push('add');
    if (shown > 0) actions.push('hide');
    const noun = matches.length === 1 ? 'match' : 'matches';
    return { text: `${matches.length} ${noun}`, actions };
};

/** The new ticks after a status action. `unannotatedTicked` is left out when unchanged. */
export const applyStatusAction = (
    action: StatusAction,
    { rows, matches, unticked }: { rows: PairRow[]; matches: PairRow[]; unticked: NamedPair[] }
): { unticked: NamedPair[]; unannotatedTicked?: boolean } => {
    const all = rows.map(toNamedPair);
    const matched = matches.map(toNamedPair);
    switch (action) {
        case 'showOnly':
            return { unticked: tickOnlyPairs(all, matched), unannotatedTicked: false };
        case 'add':
            return { unticked: tickPairs(unticked, matched) };
        case 'hide':
            return { unticked: untickPairs(unticked, matched) };
        case 'showAll':
            return { unticked: [], unannotatedTicked: true };
        case 'hideAll':
            return { unticked: all, unannotatedTicked: false };
    }
};
