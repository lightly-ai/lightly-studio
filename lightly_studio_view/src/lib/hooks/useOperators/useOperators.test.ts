import { describe, expect, it } from 'vitest';
import { createOperatorFromMetadata } from './useOperators';
import type { ParameterView, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';

const metadata: RegisteredOperatorMetadata = {
    operator_id: 'op-1',
    name: 'Blur detection'
};

const defaultParameter: ParameterView = {
    name: 'threshold',
    description: 'The blur threshold',
    default: 0.5,
    required: true,
    param_type: 'float'
};

describe('createOperatorFromMetadata', () => {
    it('maps the operator metadata and its parameters', () => {
        const operator = createOperatorFromMetadata(metadata, [defaultParameter]);

        expect(operator).toEqual({
            id: 'op-1',
            name: 'Blur detection',
            parameters: [
                {
                    name: 'threshold',
                    description: 'The blur threshold',
                    default: 0.5,
                    required: true,
                    type: 'float'
                }
            ]
        });
    });

    it('falls back to the string type when param_type is null', () => {
        const operator = createOperatorFromMetadata(metadata, [
            { ...defaultParameter, param_type: null }
        ]);

        expect(operator.parameters[0].type).toBe('string');
    });
});
