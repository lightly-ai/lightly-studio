import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
// fast_track/src/guardrails/backend -> fast_track/src/guardrails -> fast_track -> repo root
export const REPO_ROOT = resolve(__dirname, '../../../..');

/** A Python workspace member the backend guardrails judge. */
export interface BackendMember {
    /** Repo-relative directory of the member, with a trailing slash. */
    prefix: string;
    /** Repo-relative directory of its importable package, with a trailing slash. */
    srcPrefix: string;
    /** Env var holding the path to the report the member's test step wrote. */
    coverageJsonEnvVar: string;
    /** Env var set to `false` when that test step ended red. */
    testsPassedEnvVar: string;
}

/**
 * Every Python member of the uv workspace. A new sibling package is one entry here plus the
 * workflow step that writes its coverage report; nothing else in `fast_track/` names a package.
 */
export const BACKEND_MEMBERS: readonly BackendMember[] = [
    {
        prefix: 'lightly_studio/',
        srcPrefix: 'lightly_studio/src/lightly_studio/',
        coverageJsonEnvVar: 'BACKEND_COVERAGE_JSON',
        testsPassedEnvVar: 'BACKEND_TESTS_PASSED'
    },
    {
        prefix: 'lightly_studio_serve/',
        srcPrefix: 'lightly_studio_serve/src/lightly_studio_serve/',
        coverageJsonEnvVar: 'BACKEND_SERVE_COVERAGE_JSON',
        testsPassedEnvVar: 'BACKEND_SERVE_TESTS_PASSED'
    }
];

/** Absolute path of a member's directory, which is where its own tooling config applies. */
export function memberDir(member: BackendMember): string {
    return resolve(REPO_ROOT, member.prefix);
}
