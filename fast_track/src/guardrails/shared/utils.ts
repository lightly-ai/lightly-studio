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
