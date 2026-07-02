import type { Guardrail } from './context/types';

/** Always-pass placeholder until real guardrails exist. */
export const dummyGuardrail: Guardrail = {
    name: 'dummy',
    required: true,
    needsPrContext: false,
    run: async () => ({ status: 'pass', summary: 'Always passes.' })
};
