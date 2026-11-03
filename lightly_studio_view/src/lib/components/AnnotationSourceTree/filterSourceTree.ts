const normalize = (text: string) => text.trim().toLowerCase();

/** Splits a label into parts around the first match of the query, for highlighting. */
export const splitMatch = (label: string, query: string) => {
    const needle = normalize(query);
    const start = needle ? label.toLowerCase().indexOf(needle) : -1;
    if (start < 0) return { before: label, match: '', after: '' };
    const end = start + needle.length;
    return {
        before: label.slice(0, start),
        match: label.slice(start, end),
        after: label.slice(end)
    };
};
