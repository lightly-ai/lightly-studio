import { EvaluationMatchType, type ConfusionCell } from '$lib/api/lightly_studio_local';

// Query-param names for the evaluation-matches view. Keeping the contract in one
// place means the grid, the sidebar filter chips and the confusion-matrix panel all
// read and write the same URL, so the URL is the single source of truth for the
// active filters (shareable, reload-safe, and undoable via the back button).
export const MATCH_TYPES_PARAM = 'match_types';
export const CONFUSION_GT_PARAM = 'cc_gt';
export const CONFUSION_PRED_PARAM = 'cc_pred';

// Applied to every filter navigation on the matches view: replace the current
// history entry (tweaking a filter is not a new page, so it should not stack a back
// step) and keep focus/scroll so toggling a control does not jump the page.
export const MATCH_FILTER_NAV = {
    replaceState: true,
    keepFocus: true,
    noScroll: true
} as const;

export const MATCH_TYPE_ORDER: EvaluationMatchType[] = [
    EvaluationMatchType.TP,
    EvaluationMatchType.FP,
    EvaluationMatchType.FN
];

export const MATCH_TYPE_LABELS: Record<EvaluationMatchType, string> = {
    [EvaluationMatchType.TP]: 'True positive',
    [EvaluationMatchType.FP]: 'False positive',
    [EvaluationMatchType.FN]: 'False negative'
};

export function parseMatchTypesParam(searchParams: URLSearchParams): EvaluationMatchType[] {
    const raw = searchParams.get(MATCH_TYPES_PARAM);
    if (!raw) return [];
    const allowed = new Set<string>(Object.values(EvaluationMatchType));
    return raw.split(',').filter((type) => allowed.has(type)) as EvaluationMatchType[];
}

// A confusion cell always has at least one non-null label (a fully-null cell is not
// a real bucket), so the presence of either param means a cell filter is active. The
// missing side maps back to null: the false-positive (no ground truth) or
// false-negative (no prediction) margin bucket. The run id comes from the route.
export function parseConfusionCellParam(
    searchParams: URLSearchParams,
    evaluationRunId: string
): ConfusionCell | undefined {
    const gtLabel = searchParams.get(CONFUSION_GT_PARAM);
    const predLabel = searchParams.get(CONFUSION_PRED_PARAM);
    if (gtLabel === null && predLabel === null) return undefined;
    return { evaluation_run_id: evaluationRunId, gt_label: gtLabel, pred_label: predLabel };
}

function buildUrl(url: URL, searchParams: URLSearchParams): string {
    const query = searchParams.toString();
    return query ? `${url.pathname}?${query}` : url.pathname;
}

// Returns the target URL for goto(). Merges with the current search params (rather
// than rebuilding from scratch) so setting the confusion cell preserves the other
// active filters, e.g. sample_ids and match_types.
export function setConfusionCellInUrl(url: URL, cell: ConfusionCell | null): string {
    const params = new URLSearchParams(url.searchParams);
    params.delete(CONFUSION_GT_PARAM);
    params.delete(CONFUSION_PRED_PARAM);
    if (cell) {
        if (cell.gt_label != null) params.set(CONFUSION_GT_PARAM, cell.gt_label);
        if (cell.pred_label != null) params.set(CONFUSION_PRED_PARAM, cell.pred_label);
    }
    return buildUrl(url, params);
}

export function toggleMatchTypeInUrl(url: URL, matchType: EvaluationMatchType): string {
    const current = parseMatchTypesParam(url.searchParams);
    const next = current.includes(matchType)
        ? current.filter((type) => type !== matchType)
        : [...current, matchType];
    const params = new URLSearchParams(url.searchParams);
    if (next.length > 0) params.set(MATCH_TYPES_PARAM, next.join(','));
    else params.delete(MATCH_TYPES_PARAM);
    return buildUrl(url, params);
}
