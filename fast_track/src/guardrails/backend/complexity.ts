import { existsSync } from 'node:fs';
import { relative, resolve } from 'node:path';
import type { ChangedFile, Guardrail, GuardrailContext, GuardrailOutcome } from '../context/types';
import { BACKEND_MEMBERS, REPO_ROOT, memberDir } from './shared';
import { extractStdoutOrThrow, runLoggedCommand } from '../shared/utils';

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

async function runLinter(paths: string[], cwd: string): Promise<RuffViolation[]> {
    let stdout: string;
    try {
        const result = await runLoggedCommand(
            NAME,
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
            { cwd, timeout: LINTER_TIMEOUT_MS, maxBuffer: LINTER_MAX_BUFFER }
        );
        stdout = result.stdout;
    } catch (err: unknown) {
        // Ruff exits 1 when violations are found; stdout still contains valid JSON.
        stdout = extractStdoutOrThrow(err);
    }
    if (!stdout.trim()) return [];
    return JSON.parse(stdout) as RuffViolation[];
}

function backendFiles(files: ChangedFile[]): ChangedFile[] {
    return files.filter(
        (f) => f.path.endsWith('.py') && BACKEND_MEMBERS.some((m) => f.path.startsWith(m.prefix))
    );
}

function formatViolation(entry: RuffViolation): string {
    return `${relative(REPO_ROOT, entry.filename)}:${entry.location.row} — ${entry.message}`;
}

/** One ruff run per member, from that member's directory, so its own config applies. */
async function lintPerMember(files: ChangedFile[]): Promise<string[]> {
    const violations: string[] = [];
    for (const member of BACKEND_MEMBERS) {
        const paths = files
            .filter((f) => f.path.startsWith(member.prefix))
            .map((f) => resolve(REPO_ROOT, f.path));
        if (paths.length === 0) continue;
        const entries = await runLinter(paths, memberDir(member));
        violations.push(...entries.map(formatViolation));
    }
    return violations;
}

export const backendComplexityGuardrail: Guardrail = {
    name: NAME,
    required: true,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = backendFiles(await ctx.changedFiles());

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

        const violations = await lintPerMember(existingFiles);

        if (violations.length === 0) {
            return {
                status: 'pass',
                summary: `${existingFiles.length} file(s) checked, no violations.`
            };
        }

        return { status: 'fail', summary: violations.join('\n') };
    }
};
