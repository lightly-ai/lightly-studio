import type { Guardrail } from './context/types';
import { dummyGuardrail } from './dummy';
import { backendComplexityGuardrail } from './backend/complexity';
import { frontendComplexityGuardrail } from './frontend/complexity';

/** The guardrail registry. */
export const guardrails: Guardrail[] = [
    dummyGuardrail,
    frontendComplexityGuardrail,
    backendComplexityGuardrail
];

export interface SelectOptions {
    /** False locally, true in CI. */
    hasPrContext: boolean;
    /** Guardrails to run. Omit to select all; an unknown name throws. */
    guardrailNames?: string[];
}

/**
 * Choose which guardrails to run from the full set, applying two filters:
 *
 * 1. If `guardrailNames` is given, keep only those, validating them first — an
 *    unknown name throws, so a typo can't silently select nothing.
 * 2. If the environment has no PR context, drop guardrails that need the API.
 *    A guardrail named explicitly in (1) that needs PR context throws rather
 *    than being silently dropped — an explicit request we can't honour is an
 *    error, whereas an implicit "run everything" quietly skips it.
 *
 * The result preserves the input order.
 */
export function selectGuardrails(all: Guardrail[], options: SelectOptions): Guardrail[] {
    let selected = all;
    const hasExplicitGuardrails = options.guardrailNames !== undefined;

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
        if (hasExplicitGuardrails) {
            const unavailable = selected.filter((g) => g.needsPrContext).map((g) => g.name);
            if (unavailable.length > 0) {
                throw new Error(
                    `Unavailable PR context for requested guardrails: ${unavailable.join(', ')}`
                );
            }
        }
        selected = selected.filter((g) => !g.needsPrContext);
    }

    return selected;
}
