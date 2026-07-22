import { describe, expect, it, vi } from 'vitest';

import type { Octokit } from '../shared/octokit';
import { isSupersededRun } from './latest-run';

const HEAD_SHA = 'abc123';
const HEAD_BRANCH = 'feature';
const WORKFLOW_ID = 42;

function workflowRun(overrides: Record<string, unknown> = {}) {
    return {
        run_number: 11,
        run_attempt: 1,
        status: 'completed',
        conclusion: 'success',
        ...overrides
    };
}

/**
 * A fake Octokit whose `paginate` returns `runs` (as the real one does after
 * walking every page). `listWorkflowRuns` is a sentinel so a test can assert we
 * hand *that* endpoint to `paginate`. Pass `{ throws: true }` to fail the read.
 */
function fakeOctokit(runs: unknown[] | { throws: true }): Octokit {
    return {
        paginate: vi.fn().mockImplementation(async () => {
            if (!Array.isArray(runs)) throw new Error('transient GitHub API failure');
            return runs;
        }),
        rest: { actions: { listWorkflowRuns: 'runs-endpoint' } }
    } as unknown as Octokit;
}

/** Run the check as if triggered by `triggeringRun`, against the listed `runs`. */
function check(
    triggeringRun: { runNumber: number; runAttempt?: number },
    runs: unknown[] | { throws: true }
) {
    return isSupersededRun({
        octokit: fakeOctokit(runs),
        owner: 'lightly-ai',
        repo: 'lightly-studio',
        headSha: HEAD_SHA,
        headBranch: HEAD_BRANCH,
        workflowId: WORKFLOW_ID,
        runNumber: triggeringRun.runNumber,
        runAttempt: triggeringRun.runAttempt ?? 1
    });
}

describe('isSupersededRun', () => {
    it('is superseded by a newer run that reached a real conclusion', async () => {
        await expect(
            check({ runNumber: 10 }, [workflowRun({ run_number: 11, conclusion: 'success' })])
        ).resolves.toBe(true);
        // A cancelled newer run also supersedes: only a skipped run is excluded.
        await expect(
            check({ runNumber: 10 }, [workflowRun({ run_number: 11, conclusion: 'cancelled' })])
        ).resolves.toBe(true);
    });

    it('is not superseded by a newer run that only skipped', async () => {
        // A title/body edit produces a skipped run carrying no judgment;
        // suppressing this run on it would leave a passing PR unapproved.
        await expect(
            check({ runNumber: 10 }, [workflowRun({ run_number: 11, conclusion: 'skipped' })])
        ).resolves.toBe(false);
    });

    it('is not superseded by a newer run still in progress', async () => {
        await expect(
            check({ runNumber: 10 }, [
                workflowRun({ run_number: 11, status: 'in_progress', conclusion: null })
            ])
        ).resolves.toBe(false);
    });

    it('is not superseded by older or equal runs', async () => {
        await expect(
            check({ runNumber: 10 }, [
                workflowRun({ run_number: 10, run_attempt: 1 }),
                workflowRun({ run_number: 9 })
            ])
        ).resolves.toBe(false);
    });

    it('is superseded by a later attempt of the same run', async () => {
        // A later attempt of the same run supersedes an earlier one.
        await expect(
            check({ runNumber: 10, runAttempt: 1 }, [
                workflowRun({ run_number: 10, run_attempt: 2 })
            ])
        ).resolves.toBe(true);
    });

    it('queries the guardrail workflow at the trusted head and branch, every page', async () => {
        const octokit = fakeOctokit([]);
        await isSupersededRun({
            octokit,
            owner: 'lightly-ai',
            repo: 'lightly-studio',
            headSha: HEAD_SHA,
            headBranch: HEAD_BRANCH,
            workflowId: WORKFLOW_ID,
            runNumber: 10,
            runAttempt: 1
        });
        expect(octokit.paginate).toHaveBeenCalledWith('runs-endpoint', {
            owner: 'lightly-ai',
            repo: 'lightly-studio',
            workflow_id: WORKFLOW_ID,
            head_sha: HEAD_SHA,
            branch: HEAD_BRANCH,
            per_page: 100
        });
    });

    it('proceeds (not superseded) when the run listing fails', async () => {
        // Fail-closed: skipping on error would drop a genuine dismissal.
        await expect(check({ runNumber: 10 }, { throws: true })).resolves.toBe(false);
    });
});
