/**
 * Merge `selected` into `options` so a name the user just typed stays listed and
 * selected until the (later) data layer reports it back.
 */
export function withSelectedOption(options: string[], selected: string): string[] {
    if (!selected) return options;
    return [...new Set([...options, selected])];
}
