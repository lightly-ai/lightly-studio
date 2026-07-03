import { describe, expect, it } from 'vitest';

import type { RunResult } from '../guardrails/run-guardrails';
import { buildVerdict } from './verdict';

const routing = { pr_number: 7, head_sha: 'deadbeef' };

describe('buildVerdict', () => {
    it('carries the status, breakdown, and routing on a pass, with no reason', () => {
        const run: RunResult = {
            status: 'pass',
            guardrails: [{ name: 'dummy', status: 'pass', summary: 'Always passes.' }]
        };
        expect(buildVerdict(run, routing)).toEqual({
            verdict: 'pass',
            guardrails: [{ name: 'dummy', status: 'pass', summary: 'Always passes.' }],
            pr_number: 7,
            head_sha: 'deadbeef'
        });
    });

    it('adds a reason naming the failing guardrails on a fail', () => {
        const run: RunResult = {
            status: 'fail',
            guardrails: [
                { name: 'size', status: 'fail', summary: 'too big' },
                { name: 'other', status: 'pass', summary: '' }
            ]
        };
        expect(buildVerdict(run, routing).reason).toBe('Failed guardrail(s): size');
    });
});
