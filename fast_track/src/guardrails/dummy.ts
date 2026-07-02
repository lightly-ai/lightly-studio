import type { Guardrail } from './context/types';

/** Always-pass placeholder until real guardrails exist. */
export const dummyGuardrail: Guardrail = {
    name: 'dummy',
    required: true,
    needsPrContext: false,
    run: async () => ({ name: 'dummy', status: 'pass', summary: 'Always passes.' })
};
