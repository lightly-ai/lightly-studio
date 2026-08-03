import type { OperatorParameterColumn } from '$lib/hooks';

/**
 * A table column shaped exactly as the backend mapper exposes it to operator components. Columns
 * arrive from the API mapper with every field present, so the factory fills in the parts a test does
 * not care about and keeps the fixtures readable.
 */
export const column = (
    overrides: Partial<OperatorParameterColumn> = {}
): OperatorParameterColumn => ({
    name: 'prompt',
    description: 'What to segment',
    default: undefined,
    required: true,
    paramType: 'str',
    ...overrides
});
