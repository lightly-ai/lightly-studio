import { describe, expect, it } from 'vitest';

import type { Guardrail } from './context/types';
import { selectGuardrails } from './registry';

const guardrail = (name: string, availability: 'local' | 'pr-only'): Guardrail => ({
    name,
    required: true,
    availability,
    run: async () => ({ name, status: 'pass', summary: '' })
});

const local = guardrail('local-check', 'local');
const prOnly = guardrail('pr-check', 'pr-only');
const all = [local, prOnly];

describe('selectGuardrails', () => {
    it('drops pr-only guardrails when the API is unavailable', () => {
        expect(selectGuardrails(all, { includePrOnly: false })).toEqual([local]);
    });

    it('keeps pr-only guardrails when the API is available', () => {
        expect(selectGuardrails(all, { includePrOnly: true })).toEqual(all);
    });

    it('restricts to the named subset', () => {
        expect(selectGuardrails(all, { includePrOnly: true, names: ['pr-check'] })).toEqual([
            prOnly
        ]);
    });

    it('throws on an unknown name rather than passing vacuously', () => {
        expect(() => selectGuardrails(all, { includePrOnly: true, names: ['typo'] })).toThrow(
            /Unknown guardrail/
        );
    });
});
