import { describe, expect, it } from 'vitest';

import type { Guardrail } from './context/types';
import { selectGuardrails } from './registry';

const guardrail = (name: string, needsPrContext: boolean): Guardrail => ({
    name,
    required: true,
    needsPrContext,
    run: async () => ({ name, status: 'pass', summary: '' })
});

const local = guardrail('local-check', false);
const prOnly = guardrail('pr-check', true);
const all = [local, prOnly];

describe('selectGuardrails', () => {
    it('drops guardrails needing PR context when it is unavailable', () => {
        expect(selectGuardrails(all, { hasPrContext: false })).toEqual([local]);
    });

    it('keeps guardrails needing PR context when it is available', () => {
        expect(selectGuardrails(all, { hasPrContext: true })).toEqual(all);
    });

    it('restricts to the named subset', () => {
        expect(selectGuardrails(all, { hasPrContext: true, guardrailNames: ['pr-check'] })).toEqual(
            [prOnly]
        );
    });

    it('throws on an unknown name rather than passing vacuously', () => {
        expect(() =>
            selectGuardrails(all, { hasPrContext: true, guardrailNames: ['typo'] })
        ).toThrow(/Unknown guardrail/);
    });

    it('throws when an explicitly named guardrail needs unavailable PR context', () => {
        expect(() =>
            selectGuardrails(all, { hasPrContext: false, guardrailNames: ['pr-check'] })
        ).toThrow(/PR context/);
    });
});
