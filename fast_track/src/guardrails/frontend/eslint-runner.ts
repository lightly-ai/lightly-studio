import { execFile } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';
import { isExecExitOne } from '../shared/utils.js';

const execFileAsync = promisify(execFile);

const __dirname = dirname(fileURLToPath(import.meta.url));

export const FRONTEND_DIR = 'lightly_studio_view';
// fast_track/src/guardrails/frontend -> fast_track/src/guardrails -> fast_track -> repo root -> lightly_studio_view
export const FRONTEND_ABS = resolve(__dirname, '../../../..', FRONTEND_DIR);
export const FRONTEND_PREFIX = FRONTEND_DIR + '/';

const MAX_BUFFER = 32 * 1024 * 1024;

export interface EslintMessage {
    ruleId: string | null;
    severity: number;
    message: string;
    line: number;
}

export interface EslintFileResult {
    filePath: string;
    messages: EslintMessage[];
}

// Converts an absolute ESLint file path to a repo-relative path (e.g. lightly_studio_view/src/foo.ts).
export function repoRelPath(absPath: string): string {
    return FRONTEND_DIR + '/' + absPath.slice(FRONTEND_ABS.length + 1);
}

export async function runEslint(
    relPaths: string[],
    config: string,
    extraArgs: string[] = []
): Promise<EslintFileResult[]> {
    let stdout: string;
    try {
        const result = await execFileAsync(
            'node_modules/.bin/eslint',
            ['--config', config, '--format', 'json', ...extraArgs, ...relPaths],
            { cwd: FRONTEND_ABS, maxBuffer: MAX_BUFFER }
        );
        stdout = result.stdout;
    } catch (err: unknown) {
        // ESLint exits 1 when it finds lint errors; stdout still contains the JSON.
        if (!isExecExitOne(err)) throw err;
        stdout = err.stdout;
    }
    return JSON.parse(stdout) as EslintFileResult[];
}
