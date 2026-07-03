import { fileURLToPath } from 'node:url';

import type { GuardrailStatus, GuardrailResult } from '../shared/verdict';
import { GitGuardrailContext } from './context/git-context';
import type { Guardrail, GuardrailContext } from './context/types';
import { guardrails, selectGuardrails } from './registry';

export interface RunResult {
    /** `pass` iff every *required* guardrail passed. */
    status: GuardrailStatus;
    /** One entry per guardrail, in run order. */
    guardrails: GuardrailResult[];
}

/**
 * Run the guardrails sequentially and aggregate: `pass` iff every *required*
 * one passed. Pure over {@link GuardrailContext}, so CI and local runs share it.
 *
 * Guardrails run PR-author-controlled code, so a throwing guardrail is recorded
 * as a `fail` rather than crashing the run (see {@link runOne}), and required-ness
 * is read from the guardrail definition.
 */
export async function runGuardrails(
    context: GuardrailContext,
    guardrails: Guardrail[]
): Promise<RunResult> {
    const results: GuardrailResult[] = [];
    let status: GuardrailStatus = 'pass';

    for (const guardrail of guardrails) {
        const result = await runOne(guardrail, context);
        results.push(result);
        if (guardrail.required && result.status === 'fail') {
            status = 'fail';
        }
    }

    return { status, guardrails: results };
}

/**
 * Run one guardrail into a full result: the name from the definition (a
 * {@link GuardrailOutcome} carries none) plus its outcome, or a `fail` if it throws.
 */
async function runOne(guardrail: Guardrail, context: GuardrailContext): Promise<GuardrailResult> {
    try {
        const outcome = await guardrail.run(context);
        return { name: guardrail.name, ...outcome };
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
            name: guardrail.name,
            status: 'fail',
            summary: `Guardrail threw: ${message}`
        };
    }
}

// --- Local CLI -------------------------------------------------------------
//
// Judges the working tree against a base ref from a plain checkout — no
// `@actions/*`, no GitHub API. The CI entry point that writes the verdict
// artifact lands in a later PR.

/** Base ref to diff against; overridable so stacked branches can pick their base. */
const DEFAULT_BASE_REF = 'origin/main';

/** Print the registry (name, required-ness, availability) and exit. */
function listGuardrails(): void {
    console.log('Registered guardrails:');
    for (const g of guardrails) {
        const required = g.required ? 'required' : 'optional';
        const availability = g.needsPrContext ? 'pr-only' : 'local';
        console.log(`  ${g.name}  (${required}, ${availability})`);
    }
}

/** Parse `GUARDRAILS=a,b` into a name list, or undefined to run them all. */
function selectedNames(raw: string | undefined): string[] | undefined {
    if (raw === undefined) return undefined;
    const names = raw
        .split(',')
        .map((name) => name.trim())
        .filter((name) => name !== '');
    return names.length > 0 ? names : undefined;
}

async function main(argv: string[], env: NodeJS.ProcessEnv): Promise<number> {
    if (argv.includes('--list')) {
        listGuardrails();
        return 0;
    }

    const baseRef = env.BASE_REF ?? DEFAULT_BASE_REF;
    const context = new GitGuardrailContext(baseRef);
    // Local runs have no PR API, so pr-only guardrails are filtered out. An
    // explicit GUARDRAILS name that needs PR context fails fast (see selectGuardrails).
    const selected = selectGuardrails(guardrails, {
        hasPrContext: false,
        guardrailNames: selectedNames(env.GUARDRAILS)
    });

    console.log(`Fast Track guardrails — base ref: ${baseRef}\n`);
    const { status, guardrails: results } = await runGuardrails(context, selected);

    for (const result of results) {
        const mark = result.status === 'pass' ? '✓' : '✗';
        console.log(`  ${mark} ${result.name}  ${result.status}  ${result.summary}`);
    }
    console.log(`\nVerdict: ${status}`);

    return status === 'pass' ? 0 : 1;
}

// `import.meta.url` is this module's URL; `argv[1]` is the entry script. Equal
// only when this file was run directly, never when it was imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main(process.argv.slice(2), process.env)
        .then((code) => process.exit(code))
        .catch((error) => {
            console.error(error);
            process.exit(1);
        });
}
