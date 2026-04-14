import type { IFilterSet, IFilter } from '$lib/types/svar-filter';
import type { components } from '$lib/schema';
type QueryFieldSchema = components['schemas']['QueryFieldSchema'];
type WireField = components['schemas']['WireField'];
type WireTagsContains = components['schemas']['WireTagsContains'];
type WireAnd = components['schemas']['WireAnd'];
type WireOr = components['schemas']['WireOr'];
type WireExpression = WireField | WireTagsContains | WireAnd | WireOr | components['schemas']['WireNot'];

/**
 * Maps SVAR filter-type strings to wire op strings.
 * This is the only hardcoded mapping: it translates the UI library's operator
 * names to the backend wire format. Field availability and per-field operator
 * constraints come from the backend via QueryFieldSchema[].
 */
const OP_MAP: Record<string, WireField['op']> = {
    equal: '==',
    notEqual: '!=',
    greater: '>',
    greaterOrEqual: '>=',
    less: '<',
    lessOrEqual: '<='
};

function convertLeaf(
    rule: IFilter,
    schemaByShortId: Map<string, QueryFieldSchema>
): WireExpression | undefined {
    // Tag field → tags_contains node (special wire type, not a regular field)
    if (rule.field === 'tag') {
        const tag = rule.includes?.[0] ?? rule.value;
        if (!tag) return undefined;
        return { type: 'tags_contains', tag: String(tag) } satisfies WireTagsContains;
    }

    const schema = schemaByShortId.get(rule.field);
    if (!schema?.wire_name) return undefined;

    const op = OP_MAP[rule.filter ?? 'equal'];
    if (!op) return undefined;

    // Drop operators the backend doesn't support for this field.
    if (!(schema.operators as string[]).includes(op)) return undefined;

    const value = rule.value as string | number;
    if (value === undefined || value === null || value === '') return undefined;

    return { type: 'field', field: schema.wire_name, op, value } satisfies WireField;
}

function convertGroup(
    filterSet: IFilterSet,
    schemaByShortId: Map<string, QueryFieldSchema>
): WireAnd | WireOr | undefined {
    const terms = (filterSet.rules ?? [])
        .map((r) =>
            'rules' in r
                ? convertGroup(r as IFilterSet, schemaByShortId)
                : convertLeaf(r as IFilter, schemaByShortId)
        )
        .filter((t): t is WireExpression => t !== undefined);

    if (terms.length === 0) return undefined;

    const glue = filterSet.glue ?? 'and';
    return glue === 'or'
        ? ({ type: 'or', terms } satisfies WireOr)
        : ({ type: 'and', terms } satisfies WireAnd);
}

/**
 * Converts a SVAR FilterBuilder output to the canonical `WireExpression`.
 *
 * @param filterSet  Raw SVAR filter set from the query builder UI.
 * @param schemas    Field schemas fetched from `GET /api/query_fields`.
 *                   Used to resolve SVAR field IDs to wire names and to
 *                   validate that the selected operator is supported.
 * @returns `undefined` when the filter set is empty or produces no valid rules.
 */
export function svarToQueryFilter(
    filterSet: IFilterSet | null | undefined,
    schemas: QueryFieldSchema[]
): WireExpression | undefined {
    if (!filterSet?.rules?.length) return undefined;
    const schemaByShortId = new Map(schemas.map((s) => [s.id, s]));
    return convertGroup(filterSet, schemaByShortId);
}
