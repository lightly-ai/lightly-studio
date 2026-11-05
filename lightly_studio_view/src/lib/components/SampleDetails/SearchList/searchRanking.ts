const byName = (a: string, b: string) => a.localeCompare(b);

/** 0 for an exact match, 1 for a prefix, 2 for a substring, null for no match. */
const matchTier = (name: string, query: string): number | null => {
    const lower = name.toLowerCase();
    if (lower === query) return 0;
    if (lower.startsWith(query)) return 1;
    return lower.includes(query) ? 2 : null;
};

/**
 * Filters the class names by the query: exact match, then prefix, then substring. Within a tier
 * the current class comes first, then the recent classes, then alphabetical, so Enter on an empty
 * query keeps the current class. `createName` is the trimmed query when no class matches it
 * exactly.
 */
export const matchClasses = ({
    names,
    recent,
    current,
    query
}: {
    names: string[];
    recent: string[];
    current?: string;
    query: string;
}): { matches: string[]; createName: string | null } => {
    const trimmed = query.trim();
    const lowered = trimmed.toLowerCase();
    const recentRank = (name: string) => {
        if (name === current) return -1;
        const index = recent.indexOf(name);
        return index === -1 ? Infinity : index;
    };
    const ranked = names.flatMap((name) => {
        const tier = matchTier(name, lowered);
        return tier === null ? [] : [{ name, tier }];
    });
    ranked.sort(
        (a, b) =>
            a.tier - b.tier ||
            (recentRank(a.name) === recentRank(b.name)
                ? byName(a.name, b.name)
                : recentRank(a.name) - recentRank(b.name))
    );
    const hasExact = names.some((name) => name.toLowerCase() === lowered);
    return {
        matches: ranked.map(({ name }) => name),
        createName: trimmed && !hasExact ? trimmed : null
    };
};

/** Filters the annotation sources by the query: prefix, then substring, then alphabetical. */
export const matchSources = <T extends { name: string }>({
    sources,
    query
}: {
    sources: T[];
    query: string;
}): T[] => {
    const lowered = query.trim().toLowerCase();
    const ranked = sources.flatMap((source) => {
        const tier = matchTier(source.name, lowered);
        return tier === null ? [] : [{ source, tier }];
    });
    ranked.sort((a, b) => a.tier - b.tier || byName(a.source.name, b.source.name));
    return ranked.map(({ source }) => source);
};

/** The recent classes to show as chips, without the current class. */
export const recentChips = (list: string[], current: string | null, max = 3): string[] =>
    list.filter((name) => name !== current).slice(0, max);
