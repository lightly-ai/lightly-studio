import type { Guardrail } from './context/types';
import { dummyGuardrail } from './dummy';

export const guardrails: Guardrail[] = [dummyGuardrail];

export interface SelectOptions {
    /** Include `pr-only` guardrails. False locally, where the API is unavailable. */
    includePrOnly: boolean;
    /** Restrict to these names. Omit to select all. An unknown name throws. */
    names?: string[];
}

/** An unknown explicit name throws, so a typo can't drop every check into a vacuous pass. */
export function selectGuardrails(all: Guardrail[], options: SelectOptions): Guardrail[] {
    let selected = all;

    if (options.names) {
        const known = new Set(all.map((g) => g.name));
        const unknown = options.names.filter((name) => !known.has(name));
        if (unknown.length > 0) {
            throw new Error(`Unknown guardrail(s): ${unknown.join(', ')}`);
        }
        const wanted = new Set(options.names);
        selected = selected.filter((g) => wanted.has(g.name));
    }

    if (!options.includePrOnly) {
        selected = selected.filter((g) => g.availability !== 'pr-only');
    }

    return selected;
}
