import { describe, expect, it } from 'vitest';

import { buildOptOutVerdict, OPT_OUT_LABEL } from './author-opt-out';

const routing = {
    prNumber: 7,
    headSha: 'abc',
    baseRef: 'main',
    baseSha: 'base123'
};

describe('buildOptOutVerdict', () => {
    it('returns no override without the opt-out label', () => {
        expect(buildOptOutVerdict([], routing)).toBeUndefined();
    });

    it('returns an opt-out verdict bound to the PR and head', () => {
        expect(buildOptOutVerdict([OPT_OUT_LABEL], routing)).toEqual({
            verdict: 'opt_out',
            guardrails: [],
            pr_number: 7,
            head_sha: 'abc',
            base_ref: 'main',
            base_sha: 'base123',
            reason: `Author requested human review with the \`${OPT_OUT_LABEL}\` label.`
        });
    });
});
