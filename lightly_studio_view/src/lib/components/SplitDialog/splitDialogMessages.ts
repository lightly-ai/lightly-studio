export interface ClearedTag {
    name: string;
    count: number;
}

function pluralizeSamples(count: number): string {
    return `${count} ${count === 1 ? 'sample' : 'samples'}`;
}

// Joins items into a natural-language list: "a", "a and b", "a, b and c".
function joinNatural(items: string[]): string {
    if (items.length <= 1) return items.join('');
    return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

// e.g. "train (120 samples) and val (30 samples) will be cleared and reassigned."
export function formatClearedMessage(tags: ClearedTag[]): string {
    if (tags.length === 0) return '';
    const parts = tags.map((tag) => `${tag.name} (${pluralizeSamples(tag.count)})`);
    return `${joinNatural(parts)} will be cleared and reassigned.`;
}

// e.g. "test will be created." / "test and holdout will be created."
export function formatCreatedMessage(names: string[]): string {
    if (names.length === 0) return '';
    return `${joinNatural(names)} will be created.`;
}
