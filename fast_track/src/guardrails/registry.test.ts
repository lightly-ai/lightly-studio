import { describe, expect, it } from 'vitest';

import type { Guardrail } from './context/types';
import { guardrails, selectGuardrails } from './registry';

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

describe('guardrails registry', () => {
    it('has unique guardrail names', () => {
        const names = guardrails.map((g) => g.name);
        expect(new Set(names).size).toBe(names.length);
    });

    it('marks at least one guardrail as required', () => {
        expect(guardrails.some((g) => g.required)).toBe(true);
    });

    it('gives every guardrail a non-empty name', () => {
        expect(guardrails.every((g) => g.name.length > 0)).toBe(true);
    });
});
