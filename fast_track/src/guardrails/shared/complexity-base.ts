import type { ChangedFile, Guardrail, GuardrailContext } from '../context/types';
import type { GuardrailResult } from '../../shared/verdict';

/**
 * Base class for complexity guardrails. Subclasses plug in the language-specific
 * linter by implementing three methods; the run() orchestration is shared.
 *
 * TRawOutput is the raw type returned by the linter (e.g. a parsed JSON array).
 */
export abstract class ComplexityGuardrailBase<TRawOutput> implements Guardrail {
    abstract readonly name: string;
    readonly required = true;
    readonly availability = 'local';
    readonly needsPrContext = false;

    /** Return only the files this guardrail cares about (by path prefix / extension). */
    protected abstract filterFiles(files: ChangedFile[]): ChangedFile[];
    /** Invoke the linter on the given files and return its raw output. */
    protected abstract runLinter(files: ChangedFile[]): Promise<TRawOutput>;
    /** Convert raw linter output into human-readable violation strings. */
    protected abstract parseViolations(output: TRawOutput): string[];

    async run(ctx: GuardrailContext): Promise<GuardrailResult> {
        const files = await ctx.changedFiles();
        const relevant = this.filterFiles(files);

        if (relevant.length === 0) {
            return { name: this.name, status: 'pass', summary: '0 file(s) checked.' };
        }

        const raw = await this.runLinter(relevant);
        const violations = this.parseViolations(raw);

        if (violations.length === 0) {
            return {
                name: this.name,
                status: 'pass',
                summary: `${relevant.length} file(s) checked, no violations.`
            };
        }

        return { name: this.name, status: 'fail', summary: violations.join('\n') };
    }
}
