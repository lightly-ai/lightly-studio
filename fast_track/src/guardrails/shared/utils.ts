export function pct(ratio: number): string {
    return `${(ratio * 100).toFixed(1)}%`;
}

// Parses a unified diff patch and returns the set of line numbers (in the new file)
// for lines that were added (i.e. starting with '+' but not the '+++' file header).
export function extractAddedLines(patch: string): Set<number> {
    const added = new Set<number>();
    let newLine = 0;

    for (const line of patch.split('\n')) {
        const hunkMatch = line.match(/^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
        if (hunkMatch) {
            newLine = parseInt(hunkMatch[1] ?? '0', 10);
            continue;
        }
        // Skip file-level diff headers (+++, ---, diff, index, new mode, old mode).
        if (/^(\+\+\+|---|diff |index |new |old )/.test(line)) continue;

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
