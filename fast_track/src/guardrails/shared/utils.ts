import { execFile } from 'node:child_process';
import type { ExecFileOptions } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

export function pct(ratio: number): string {
    return `${(ratio * 100).toFixed(1)}%`;
}

export interface CommandResult {
    stdout: string;
    stderr: string;
}

/**
 * Runs a command via execFile and always echoes its stdout/stderr to the CI
 * console — on both the success and the error path — before returning or
 * re-throwing. Guardrails spawn third-party tools (ruff, pytest, vitest) whose
 * output is otherwise swallowed; surfacing it lets a CI run be inspected.
 *
 * The original error is re-thrown unchanged, so callers keep their own exit-code
 * handling (e.g. ruff exits 1 on violations, pytest on a failing test).
 */
export async function runLoggedCommand(
    file: string,
    args: string[],
    options: ExecFileOptions
): Promise<CommandResult> {
    const label = `${file} ${args.join(' ')}`;
    try {
        const { stdout, stderr } = await execFileAsync(file, args, options);
        logCommandOutput(label, stdout, stderr);
        return { stdout: asText(stdout), stderr: asText(stderr) };
    } catch (err) {
        const { stdout, stderr } = err as { stdout?: unknown; stderr?: unknown };
        logCommandOutput(label, stdout, stderr);
        throw err;
    }
}

// execFile always yields string stdout/stderr with the default encoding; coerce
// defensively so a partial value (e.g. from a test stub) can't crash the wrapper.
function asText(value: unknown): string {
    return typeof value === 'string' ? value : '';
}

function logCommandOutput(label: string, stdout: unknown, stderr: unknown): void {
    console.log(`$ ${label}`);
    const out = asText(stdout).trimEnd();
    const err = asText(stderr).trimEnd();
    if (out) console.log(out);
    if (err) console.error(err);
}

// Parses a unified diff patch and returns the set of line numbers (in the new file)
// for lines that were added (i.e. starting with '+' but not the '+++' file header).
export function extractAddedLines(patch: string): Set<number> {
    const added = new Set<number>();
    let newLine = 0;
    let inHunk = false;

    for (const line of patch.split('\n')) {
        const hunkMatch = line.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
        if (hunkMatch) {
            newLine = parseInt(hunkMatch[1] ?? '0', 10);
            inHunk = true;
            continue;
        }
        // Skip file-level diff headers (+++, ---, diff, index, new mode, old mode).
        // Only apply before the first hunk; inside a hunk these patterns can appear
        // as legitimate added-line content (e.g. an added line whose text starts with +++).
        if (!inHunk && /^(\+\+\+|---|diff |index |new |old )/.test(line)) continue;

        if (line.startsWith('+')) {
            added.add(newLine);
            newLine++;
        } else if (line.startsWith(' ')) {
            // Context line — present in new file but not added.
            newLine++;
        }
        // Lines starting with '-' do not appear in the new file; newLine stays put.
    }

    return added;
}
/**
 * Extracts stdout from a process error when the exit code is 1.
 * Some linters (e.g. Ruff) exit with code 1 when violations are found,
 * but still write valid output to stdout.
 * Returns the stdout string if the error matches, otherwise re-throws.
 */
export function extractStdoutOrThrow(err: unknown): string {
    if (
        err !== null &&
        typeof err === 'object' &&
        'code' in err &&
        (err as { code: unknown }).code === 1 &&
        'stdout' in err &&
        typeof (err as { stdout: unknown }).stdout === 'string'
    ) {
        return (err as { stdout: string }).stdout;
    }
    throw err;
}
