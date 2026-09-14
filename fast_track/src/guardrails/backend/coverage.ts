import type { ChangedFile, Guardrail, GuardrailContext, GuardrailOutcome } from '../context/types';
import { createCoverageGuardrail, type LineCoverage } from '../shared/full-suite-coverage';
import { BACKEND_MEMBERS, type BackendMember } from './shared';

const NAME = 'backend/coverage';

export interface CoverageFileData {
    executed_lines: number[];
    missing_lines: number[];
}

interface CoverageData {
    files: Record<string, CoverageFileData>;
}

export function filterBackendFiles(files: ChangedFile[]): ChangedFile[] {
    return BACKEND_MEMBERS.flatMap((member) => filterMemberFiles(member, files));
}

/**
 * Normalises a coverage.py JSON report into repo-relative per-line coverage. `prefix` is the
 * member directory pytest ran in, which is what the report's keys are relative to.
 */
export function parseBackendReport(raw: string, prefix: string): LineCoverage {
    const data = JSON.parse(raw) as CoverageData;
    const coverage: LineCoverage = new Map();
    for (const [key, entry] of Object.entries(data.files)) {
        coverage.set(prefix + key, {
            executable: new Set([...entry.executed_lines, ...entry.missing_lines]),
            covered: new Set(entry.executed_lines)
        });
    }
    return coverage;
}

// One sub-guardrail per member, each reading that member's own report. They share a name: the
// verdict carries a single backend/coverage entry however many members a pull request touches.
const MEMBER_GUARDRAILS = BACKEND_MEMBERS.map((member) => ({
    member,
    guardrail: createCoverageGuardrail({
        name: NAME,
        coverageJsonEnvVar: member.coverageJsonEnvVar,
        testsPassedEnvVar: member.testsPassedEnvVar,
        filterFiles: (files) => filterMemberFiles(member, files),
        parseReport: (raw) => parseBackendReport(raw, member.prefix)
    })
}));

export const backendCoverageGuardrail: Guardrail = {
    name: NAME,
    required: true,

    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = await ctx.changedFiles();
        // Only members the pull request touches run, so the summary never carries a
        // "0 file(s) checked." line for a member that has nothing to say.
        const active = MEMBER_GUARDRAILS.filter(
            (entry) => filterMemberFiles(entry.member, files).length > 0
        );

        if (active.length === 0) {
            return { status: 'pass', summary: '0 file(s) checked.' };
        }

        const outcomes = await Promise.all(active.map((entry) => entry.guardrail.run(ctx)));
        return {
            status: outcomes.some((outcome) => outcome.status === 'fail') ? 'fail' : 'pass',
            summary: outcomes.map((outcome) => outcome.summary).join('\n')
        };
    }
};

// `examples/` has no `__init__.py`, so coverage.py's source scan never reaches it.
// `vendor/` is third-party code we do not hold to a coverage bar.
const EXCLUDED_DIRS = ['migrations', 'examples', 'vendor'];

function filterMemberFiles(member: BackendMember, files: ChangedFile[]): ChangedFile[] {
    return files.filter(
        (f) =>
            f.path.startsWith(member.srcPrefix) &&
            f.path.endsWith('.py') &&
            !isExcludedBackendPath(f.path)
    );
}

function isExcludedBackendPath(path: string): boolean {
    const name = path.split('/').at(-1) ?? '';
    return (
        EXCLUDED_DIRS.some((dir) => path.includes(`/${dir}/`)) ||
        (name.startsWith('test_') && name.endsWith('.py')) ||
        name === 'conftest.py' ||
        name === '__init__.py'
    );
}
