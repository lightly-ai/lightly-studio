/** Above this many fields, the section adds a field search. */
export const MANY_FIELDS = 8;

/** Whether a field name contains the search text, ignoring case. */
export const matchesFieldSearch = (field: string, search: string): boolean =>
    field.toLowerCase().includes(search.trim().toLowerCase());
