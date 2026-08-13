import { describe, expect, it } from 'vitest';

import type { Guardrail } from './context/types';
import { selectGuardrails } from './registry';

const guardrail = (name: string): Guardrail => ({
    name,
    required: true,
    run: async () => ({ status: 'pass', summary: '' })
});

const first = guardrail('first-check');
const second = guardrail('second-check');
const all = [first, second];

describe('selectGuardrails', () => {
    it('selects all when no names are given', () => {
        expect(selectGuardrails(all, {})).toEqual(all);
    });

    it('restricts to the named subset', () => {
        expect(selectGuardrails(all, { guardrailNames: ['second-check'] })).toEqual([second]);
    });

    it('preserves the input order regardless of the requested order', () => {
        expect(selectGuardrails(all, { guardrailNames: ['second-check', 'first-check'] })).toEqual(
            all
        );
    });

    it('throws on an unknown name rather than passing vacuously', () => {
        expect(() => selectGuardrails(all, { guardrailNames: ['typo'] })).toThrow(
            /Unknown guardrail/
        );
    });
});
