import { describe, expect, it } from 'vitest';

import type { Verdict } from '../shared/verdict';
import { isVerdict } from './verdict-schema';

// Canonical well-formed pass artifact. Tests override its fields.
function artifact(): Verdict {
    return {
        verdict: 'pass',
        guardrails: [{ name: 'dummy', status: 'pass', summary: 'ok' }],
        pr_number: 7,
        head_sha: 'abc123',
        base_ref: 'main',
        base_sha: 'base123'
    };
}

describe('isVerdict', () => {
    it('accepts a well-formed pass verdict', () => {
        expect(isVerdict(artifact())).toBe(true);
    });

    it('accepts a well-formed fail verdict', () => {
        expect(isVerdict({ ...artifact(), verdict: 'fail', reason: 'a guardrail failed' })).toBe(
            true
        );
    });

    // Rejection cases.
    it.each<[string, unknown]>([
        ['a non-object', undefined],
        [
            'an opt_out status (synthesized from the live label, never parsed)',
            { ...artifact(), verdict: 'opt_out' }
        ],
        ['a non-string status', { ...artifact(), verdict: ['pass'] }],
        ['a missing guardrails array', { ...artifact(), guardrails: undefined }],
        ['a malformed guardrail entry', { ...artifact(), guardrails: [{ name: 'dummy' }] }],
        [
            'duplicate guardrail names',
            {
                ...artifact(),
                guardrails: [
                    { name: 'dummy', status: 'pass', summary: 'ok' },
                    { name: 'dummy', status: 'fail', summary: 'again' }
                ]
            }
        ],
        ['a non-integer pr_number', { ...artifact(), pr_number: 1.5 }],
        ['a non-string head_sha', { ...artifact(), head_sha: 123 }],
        ['a non-string base_ref', { ...artifact(), base_ref: 123 }],
        ['a non-string base_sha', { ...artifact(), base_sha: 123 }],
        ['a non-string reason', { ...artifact(), reason: 42 }]
    ])('rejects %s', (_description, value) => {
        expect(isVerdict(value)).toBe(false);
    });
});
