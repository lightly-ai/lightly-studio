import { existsSync } from 'node:fs';
import { extname, resolve } from 'node:path';
import type { ESLint } from 'eslint';
import type { Guardrail, GuardrailContext, GuardrailOutcome } from '../context/types';
import { FRONTEND_ABS, FRONTEND_PREFIX, repoRelPath, runEslint } from './eslint-runner';

const EXTENSIONS = new Set(['.js', '.ts', '.svelte']);
const ESLINT_CONFIG = 'eslint.complexity.config.js';
const ESLINT_ERROR_SEVERITY = 2;

export const frontendComplexityGuardrail: Guardrail = {
    name: 'frontend/complexity',
    required: true,
    needsPrContext: false,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = (await ctx.changedFiles()).filter(
            (f) => f.path.startsWith(FRONTEND_PREFIX) && EXTENSIONS.has(extname(f.path))
        );

        if (files.length === 0) {
            return { status: 'pass', summary: '0 file(s) checked.' };
        }

        // Exclude deleted files — they no longer exist on disk and cannot be linted.
        const existingFiles = files.filter((f) =>
            existsSync(resolve(FRONTEND_ABS, f.path.slice(FRONTEND_PREFIX.length)))
        );

        if (existingFiles.length === 0) {
            return { status: 'pass', summary: 'All changed frontend files were deleted.' };
        }

        const relPaths = existingFiles.map((f) => f.path.slice(FRONTEND_PREFIX.length));
        const results: ESLint.LintResult[] = await runEslint(relPaths, ESLINT_CONFIG);
        const violations = results.flatMap((file) =>
            file.messages
                .filter((msg) => msg.severity === ESLINT_ERROR_SEVERITY)
                .map((msg) => `${repoRelPath(file.filePath)}:${msg.line} — ${msg.message}`)
        );

        if (violations.length === 0) {
            return {
                status: 'pass',
                summary: `${existingFiles.length} file(s) checked, no violations.`
            };
        }

        return { status: 'fail', summary: violations.join('\n') };
    }
};
