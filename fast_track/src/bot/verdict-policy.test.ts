import { describe, expect, it } from 'vitest';

import { OPT_OUT_LABEL } from '../guardrails/author-opt-out';
import type { Verdict } from '../shared/verdict';
import type { BotTarget } from './derive-target';
import { effectiveVerdict, verdictMatchesTarget } from './verdict-policy';

// Object mothers: a happy-path target and pass verdict. Each test overrides only
// the field it is about, so the meaningful delta stays visible in the test body.
function target(overrides: Partial<BotTarget> = {}): BotTarget {
    return {
        prNumber: 7,
        headSha: 'abc123',
        baseRef: 'main',
        baseSha: 'base123',
        labels: [],
        ...overrides
    };
}

function passVerdict(overrides: Partial<Verdict> = {}): Verdict {
    return {
        verdict: 'pass',
        guardrails: [{ name: 'dummy', status: 'pass', summary: 'ok' }],
        pr_number: 7,
        head_sha: 'abc123',
        base_ref: 'main',
        base_sha: 'base123',
        ...overrides
    };
}

describe('effectiveVerdict', () => {
    it('returns the artifact verdict when a current pass matches the target', () => {
        const artifact = passVerdict();

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: artifact },
            target()
        );

        expect(result).toEqual(artifact);
    });

    it('passes when only an optional (non-required) guardrail failed', () => {
        const artifact = passVerdict({
            guardrails: [
                { name: 'dummy', status: 'pass', summary: 'ok' },
                { name: 'advisory', status: 'fail', summary: 'consider simplifying' }
            ]
        });

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: artifact },
            target()
        );

        expect(result.verdict).toBe('pass');
    });

    it('opts out when the target carries the opt-out label, ignoring a passing artifact', () => {
        const result = effectiveVerdict(
            {
                guardrailsSucceeded: true,
                requiredGuardrailNames: ['dummy'],
                verdict: passVerdict()
            },
            target({ labels: [OPT_OUT_LABEL] })
        );

        expect(result.verdict).toBe('opt_out');
    });

    it('fails when the guardrail workflow did not complete', () => {
        const result = effectiveVerdict(
            { guardrailsSucceeded: false, requiredGuardrailNames: ['dummy'], verdict: undefined },
            target()
        );

        expect(result.verdict).toBe('fail');
    });

    it('fails a structurally invalid verdict artifact', () => {
        const malformed = { verdict: 'pass' };

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: malformed },
            target()
        );

        expect(result.verdict).toBe('fail');
    });

    it('fails a pass that is missing a required guardrail', () => {
        const artifact = passVerdict({ guardrails: [] });

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: artifact },
            target()
        );

        expect(result.verdict).toBe('fail');
    });

    it('fails a pass whose required guardrail did not pass', () => {
        const artifact = passVerdict({
            guardrails: [{ name: 'dummy', status: 'fail', summary: 'failed' }]
        });

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: artifact },
            target()
        );

        expect(result.verdict).toBe('fail');
    });

    it('fails an opt-out artifact when the target is not labelled (stale or spoofed)', () => {
        const artifact = passVerdict({
            verdict: 'opt_out',
            guardrails: [],
            reason: 'Author requested human review.'
        });

        const result = effectiveVerdict(
            { guardrailsSucceeded: true, requiredGuardrailNames: ['dummy'], verdict: artifact },
            target()
        );

        expect(result.verdict).toBe('fail');
    });

    it('fails a verdict bound to an earlier base revision', () => {
        const result = effectiveVerdict(
            {
                guardrailsSucceeded: true,
                requiredGuardrailNames: ['dummy'],
                verdict: passVerdict()
            },
            target({ baseRef: 'release', baseSha: 'newbase' })
        );

        expect(result.verdict).toBe('fail');
    });
});

describe('verdictMatchesTarget', () => {
    it('accepts a verdict aligned with its target', () => {
        expect(verdictMatchesTarget(passVerdict(), target())).toBe(true);
    });

    it('rejects a verdict whose PR number differs', () => {
        expect(verdictMatchesTarget(passVerdict({ pr_number: 8 }), target())).toBe(false);
    });

    it('rejects a verdict whose head SHA differs', () => {
        expect(verdictMatchesTarget(passVerdict(), target({ headSha: 'newer' }))).toBe(false);
    });

    it('rejects a verdict whose base ref differs', () => {
        expect(verdictMatchesTarget(passVerdict(), target({ baseRef: 'release' }))).toBe(false);
    });

    it('rejects a verdict whose base SHA differs', () => {
        expect(verdictMatchesTarget(passVerdict(), target({ baseSha: 'newbase' }))).toBe(false);
    });

    it('rejects a verdict when the target is opted out', () => {
        expect(verdictMatchesTarget(passVerdict(), target({ labels: [OPT_OUT_LABEL] }))).toBe(
            false
        );
    });
});
