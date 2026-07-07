import { fileURLToPath } from 'node:url';

import { GitGuardrailContext } from './context/git-context';
import { guardrails, selectGuardrails } from './registry';
import { runGuardrails } from './run-guardrails';

// Local CLI: judges the branch's committed changes from a plain checkout — no
// GitHub API. The CI entry that writes the verdict artifact lands in a later PR.

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
    // Validate the base ref before judging: an empty or unresolvable ref would
    // otherwise diff against nothing and report a vacuous pass (see git-context).
    await context.assertBaseRefResolves();
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

// Run only when invoked directly, not when imported.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main(process.argv.slice(2), process.env)
        .then((code) => process.exit(code))
        .catch((error) => {
            console.error(error);
            process.exit(1);
        });
}
