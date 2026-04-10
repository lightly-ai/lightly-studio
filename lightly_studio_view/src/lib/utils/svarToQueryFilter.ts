import type { IFilterSet, IFilter } from '$lib/types/svar-filter';
import type {
    WireExpression,
    WireField,
    WireTagsContains,
    WireAnd,
    WireOr
} from '$lib/types/queryFilter';

/**
 * Maps SVAR field IDs to canonical wire-format field names.
 * Matches the `_FIELD_REGISTRY` in `core/dataset_query/wire.py`.
 */
const FIELD_MAP: Record<string, string> = {
    file_name: 'image.file_name',
    width: 'image.width',
    height: 'image.height',
    created_at: 'image.created_at'
};

/**
 * Maps SVAR filter-type strings to wire op strings.
 * Only ordinal and comparable ops — no text operators (not in Python API).
 */
const OP_MAP: Record<string, WireField['op']> = {
    equal: '==',
    notEqual: '!=',
    greater: '>',
    greaterOrEqual: '>=',
    less: '<',
    lessOrEqual: '<='
};

function convertLeaf(rule: IFilter): WireExpression | undefined {
    // Tag field → tags_contains node
    if (rule.field === 'tag') {
        const tag = rule.includes?.[0] ?? rule.value;
        if (!tag) return undefined;
        return { type: 'tags_contains', tag: String(tag) } satisfies WireTagsContains;
    }

    const wireField = FIELD_MAP[rule.field];
    if (!wireField) return undefined;

    const op = OP_MAP[rule.filter ?? 'equal'];
    if (!op) return undefined;

    const value = rule.value as string | number;
    if (value === undefined || value === null || value === '') return undefined;

    return { type: 'field', field: wireField, op, value } satisfies WireField;
}

function convertGroup(filterSet: IFilterSet): WireAnd | WireOr | undefined {
    const terms = (filterSet.rules ?? [])
        .map((r) => ('rules' in r ? convertGroup(r as IFilterSet) : convertLeaf(r as IFilter)))
        .filter((t): t is WireExpression => t !== undefined);

    if (terms.length === 0) return undefined;
    if (terms.length === 1) {
        // Collapse single-term groups — wrap in the correct combinator to satisfy
        // TypeScript, but the backend handles a bare expression too.
        const glue = filterSet.glue ?? 'and';
        return glue === 'or'
            ? ({ type: 'or', terms } satisfies WireOr)
            : ({ type: 'and', terms } satisfies WireAnd);
    }

    const glue = filterSet.glue ?? 'and';
    return glue === 'or'
        ? ({ type: 'or', terms } satisfies WireOr)
        : ({ type: 'and', terms } satisfies WireAnd);
}

/**
 * Converts a SVAR FilterBuilder output to the canonical `WireExpression`.
 * Returns `undefined` when the filter set is empty or produces no valid rules.
 */
export function svarToQueryFilter(
    filterSet: IFilterSet | null | undefined
): WireExpression | undefined {
    if (!filterSet?.rules?.length) return undefined;
    return convertGroup(filterSet);
}
