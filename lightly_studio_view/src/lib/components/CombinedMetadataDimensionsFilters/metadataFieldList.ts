/** Above this many fields, the section adds a field search and starts with fields collapsed. */
export const MANY_FIELDS = 8;

/** Whether a field name contains the search text, ignoring case. */
export const matchesFieldSearch = (field: string, search: string): boolean =>
    field.toLowerCase().includes(search.trim().toLowerCase());

/**
 * Whether a field shows its slider or values.
 *
 * A field the user opened or closed keeps that state. The others start open, unless the
 * section has more than `MANY_FIELDS` fields.
 */
export const isFieldExpanded = (
    overrides: Record<string, boolean>,
    field: string,
    fieldCount: number
): boolean => overrides[field] ?? fieldCount <= MANY_FIELDS;
