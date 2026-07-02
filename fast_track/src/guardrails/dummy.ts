import type { Guardrail } from './context/types';

/** Always-pass placeholder until real guardrails exist. */
export const dummyGuardrail: Guardrail = {
    name: 'dummy',
    required: true,
    availability: 'local',
    run: async () => ({ name: 'dummy', status: 'pass', summary: 'Always passes.' })
};
