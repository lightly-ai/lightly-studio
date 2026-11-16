/** Moves the entry to the front of the recent list and keeps at most `max` entries. */
export const pushRecent = (list: string[], name: string, max = 5): string[] => {
    const trimmed = name.trim();
    if (!trimmed) return list;
    return [trimmed, ...list.filter((item) => item !== trimmed)].slice(0, max);
};
