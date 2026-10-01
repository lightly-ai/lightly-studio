import type { OperatorParameterColumn } from '$lib/hooks';

/**
 * A table column as the API mapper exposes it, where every field is present. Overrides let a test
 * name only the fields it cares about.
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
