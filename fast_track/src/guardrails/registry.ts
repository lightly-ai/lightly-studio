import type { Guardrail } from './context/types';
import { backendComplexityGuardrail } from './backend/complexity';
import { frontendComplexityGuardrail } from './frontend/complexity';
import { backendCoverageGuardrail } from './backend/coverage';
import { diffSizeGuardrail } from './diff-size';
import { frontendCoverageGuardrail } from './frontend/coverage';

/** The guardrail registry. */
export const guardrails: Guardrail[] = [
    frontendComplexityGuardrail,
    backendComplexityGuardrail,
    backendCoverageGuardrail,
    diffSizeGuardrail,
    frontendCoverageGuardrail
];

export interface SelectOptions {
    /** Guardrails to run. Omit to select all; an unknown name throws. */
    guardrailNames?: string[];
}

/**
 * Choose which guardrails to run from the full set.
 *
 * If `guardrailNames` is given, keep only those, validating them first — an
 * unknown name throws, so a typo can't silently select nothing.
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

    return selected;
}
