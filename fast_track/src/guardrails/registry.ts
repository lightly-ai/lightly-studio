import type { Guardrail } from './context/types';
import { dummyGuardrail } from './dummy';

/** The guardrail registry. */
export const guardrails: Guardrail[] = [dummyGuardrail];

export interface SelectOptions {
    /** False locally, true in CI. */
    hasPrContext: boolean;
    /** Guardrails to run. Omit to select all; an unknown name throws. */
    guardrailNames?: string[];
}

/**
 * Choose which guardrails to run from the full set, applying two filters:
 *
 * 1. If `guardrailNames` is given, keep only those (and validate them first —
 *    an unknown name throws, so a typo can't silently drop every check into a
 *    vacuous pass).
 * 2. If the environment has no PR context, drop guardrails that need the API.
 *
 * The result preserves the input order.
 */
export function selectGuardrails(all: Guardrail[], options: SelectOptions): Guardrail[] {
    let selected = all;

    if (options.guardrailNames) {
        const known = new Set(all.map((g) => g.name));
        const unknown = options.guardrailNames.filter((name) => !known.has(name));
        if (unknown.length > 0) {
            throw new Error(`Unknown guardrail(s): ${unknown.join(', ')}`);
        }
        const wanted = new Set(options.guardrailNames);
        selected = selected.filter((g) => wanted.has(g.name));
    }

    if (!options.hasPrContext) {
        selected = selected.filter((g) => !g.needsPrContext);
    }

    return selected;
}
