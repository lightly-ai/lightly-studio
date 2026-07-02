interface ExecExitOne {
    code: 1;
    stdout: string;
}

/**
 * Returns true when a promisified execFile error is an exit-code-1 failure
 * with stdout populated. This happens when tools (e.g. ESLint) use exit code 1
 * to signal findings rather than a hard failure, so stdout still contains
 * parseable output.
 */
export function isExecExitOne(err: unknown): err is ExecExitOne {
    return (
        err !== null &&
        typeof err === 'object' &&
        'code' in err &&
        (err as { code: unknown }).code === 1 &&
        'stdout' in err &&
        typeof (err as { stdout: unknown }).stdout === 'string'
    );
}
