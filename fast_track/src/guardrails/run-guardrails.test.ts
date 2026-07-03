import { describe, expect, it } from 'vitest';

import type { GuardrailStatus } from '../shared/verdict';
import type { Guardrail, GuardrailContext } from './context/types';
import { runGuardrails } from './run-guardrails';

const context: GuardrailContext = {
    baseRef: 'origin/main',
    changedFiles: async () => []
};

/** A guardrail that reports a fixed status. */
const stub = (name: string, status: GuardrailStatus, required = true): Guardrail => ({
    name,
    required,
    needsPrContext: false,
    run: async () => ({ status, summary: '' })
});

/** A guardrail that throws instead of returning a result. */
const throwing = (name: string, required = true): Guardrail => ({
    name,
    required,
    needsPrContext: false,
    run: async () => {
        throw new Error('boom');
    }
});

describe('runGuardrails', () => {
    it('passes when every required guardrail passes', async () => {
        const result = await runGuardrails(context, [stub('a', 'pass'), stub('b', 'pass')]);
        expect(result.status).toBe('pass');
    });

    it('fails when any required guardrail fails', async () => {
        const result = await runGuardrails(context, [stub('a', 'pass'), stub('b', 'fail')]);
        expect(result.status).toBe('fail');
    });

    it('ignores a failing optional guardrail in the aggregate', async () => {
        const result = await runGuardrails(context, [
            stub('required', 'pass'),
            stub('optional', 'fail', false)
        ]);
        expect(result.status).toBe('pass');
    });

    it('reports every guardrail in run order, named from the definition', async () => {
        const result = await runGuardrails(context, [stub('a', 'pass'), stub('b', 'fail')]);
        expect(result.guardrails.map((g) => g.name)).toEqual(['a', 'b']);
    });

    it('records a throwing guardrail as a fail instead of crashing', async () => {
        const result = await runGuardrails(context, [throwing('exploder')]);
        expect(result.status).toBe('fail');
        expect(result.guardrails).toEqual([
            { name: 'exploder', status: 'fail', summary: 'Guardrail threw: boom' }
        ]);
    });

    it('lets a throwing optional guardrail pass the run', async () => {
        const result = await runGuardrails(context, [
            stub('required', 'pass'),
            throwing('optional', false)
        ]);
        expect(result.status).toBe('pass');
    });
});
