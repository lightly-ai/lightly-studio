import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import { relative, resolve } from 'node:path';
import { promisify } from 'node:util';
import type { Guardrail, GuardrailContext, GuardrailOutcome } from '../context/types';
import { REPO_ROOT, BACKEND_DIR } from './shared';
import { extractStdoutOrThrow } from '../shared/utils';

const execFileAsync = promisify(execFile);
const BACKEND_PREFIX = 'lightly_studio/';
const NAME = 'backend/complexity';
const COMPLEXITY_RULE = 'C901';
const LINTER_TIMEOUT_MS = 60_000;
const LINTER_MAX_BUFFER = 10 * 1024 * 1024;

interface RuffViolation {
    code: string;
    filename: string;
    message: string;
    location: { row: number; column: number };
}

async function runLinter(paths: string[]): Promise<RuffViolation[]> {
    let stdout: string;
    try {
        const result = await execFileAsync(
            'uv',
            [
                'run',
                'ruff',
                'check',
                '--select',
                COMPLEXITY_RULE,
                '--output-format',
                'json',
                ...paths
            ],
            { cwd: BACKEND_DIR, timeout: LINTER_TIMEOUT_MS, maxBuffer: LINTER_MAX_BUFFER }
        );
        stdout = result.stdout;
    } catch (err: unknown) {
        // Ruff exits 1 when violations are found; stdout still contains valid JSON.
        stdout = extractStdoutOrThrow(err);
    }
    if (!stdout.trim()) return [];
    return JSON.parse(stdout) as RuffViolation[];
}

export const backendComplexityGuardrail: Guardrail = {
    name: NAME,
    required: true,
    needsPrContext: false,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = (await ctx.changedFiles()).filter(
            (f) => f.path.startsWith(BACKEND_PREFIX) && f.path.endsWith('.py')
        );

        if (files.length === 0) {
            return { status: 'pass', summary: '0 file(s) checked.' };
        }

        // Exclude deleted files — they no longer exist on disk and cannot be linted.
        const existingFiles = files.filter((f) => existsSync(resolve(REPO_ROOT, f.path)));

        if (existingFiles.length === 0) {
            return {
                status: 'pass',
                summary: 'All changed backend files were deleted.'
            };
        }

        const violations = (
            await runLinter(existingFiles.map((f) => resolve(REPO_ROOT, f.path)))
        ).map(
            (entry) =>
                `${relative(REPO_ROOT, entry.filename)}:${entry.location.row} — ${entry.message}`
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
