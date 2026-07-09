export function pct(ratio: number): string {
    return `${(ratio * 100).toFixed(1)}%`;
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
