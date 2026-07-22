import { describe, expect, it } from 'vitest';

import type { RunResult } from './run-guardrails';
import { buildVerdict } from './build-verdict';

const routing = {
    prNumber: 42,
    headSha: 'deadbeef',
    baseRef: 'main',
    baseSha: 'base123'
};

describe('buildVerdict', () => {
    it('carries the status, breakdown, and routing on a pass — no reason', () => {
        const run: RunResult = {
            status: 'pass',
            guardrails: [{ name: 'dummy', status: 'pass', summary: 'ok' }]
        };

        expect(buildVerdict(run, routing)).toEqual({
            verdict: 'pass',
            guardrails: [{ name: 'dummy', status: 'pass', summary: 'ok' }],
            pr_number: 42,
            head_sha: 'deadbeef',
            base_ref: 'main',
            base_sha: 'base123'
        });
    });

    it('names every failing guardrail on a fail, joined, excluding the passing ones', () => {
        const run: RunResult = {
            status: 'fail',
            guardrails: [
                { name: 'diff-size', status: 'fail', summary: 'too big' },
                { name: 'passing', status: 'pass', summary: 'ok' },
                { name: 'coverage', status: 'fail', summary: 'dropped 3%' }
            ]
        };

        const verdict = buildVerdict(run, routing);
        expect(verdict.verdict).toBe('fail');
        expect(verdict.reason).toBe(
            'Failed guardrails: diff-size (too big), coverage (dropped 3%)'
        );
    });

    it('falls back to a generic reason if a fail reports no failing guardrail', () => {
        const run: RunResult = { status: 'fail', guardrails: [] };
        expect(buildVerdict(run, routing).reason).toBe(
            'One or more required guardrails did not pass.'
        );
    });
});
