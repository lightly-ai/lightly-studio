import { describe, expect, it } from 'vitest';
import { createOperatorFromMetadata } from './useOperators';
import type {
    ParameterColumnView,
    ParameterView,
    RegisteredOperatorMetadata
} from '$lib/api/lightly_studio_local';

const metadata: RegisteredOperatorMetadata = {
    operator_id: 'op-1',
    name: 'Blur detection'
};

const defaultColumn: ParameterColumnView = {
    name: 'label',
    description: 'The label to assign',
    default: 'blurry',
    required: true,
    param_type: 'str'
};

const defaultParameter: ParameterView = {
    name: 'threshold',
    description: 'The blur threshold',
    default: 0.5,
    required: true,
    param_type: 'float',
    columns: null
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
                    type: 'float',
                    columns: undefined
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

    it('maps the columns of a table parameter', () => {
        const operator = createOperatorFromMetadata(metadata, [
            { ...defaultParameter, param_type: 'table', columns: [defaultColumn] }
        ]);

        expect(operator.parameters[0].columns).toEqual([
            {
                name: 'label',
                description: 'The label to assign',
                default: 'blurry',
                required: true,
                paramType: 'str'
            }
        ]);
    });

    it('converts a null column param_type to undefined', () => {
        const operator = createOperatorFromMetadata(metadata, [
            {
                ...defaultParameter,
                param_type: 'table',
                columns: [{ ...defaultColumn, param_type: null }]
            }
        ]);

        expect(operator.parameters[0].columns?.[0].paramType).toBeUndefined();
    });

    it('maps an empty column list of a table parameter without columns', () => {
        const operator = createOperatorFromMetadata(metadata, [
            { ...defaultParameter, param_type: 'table', columns: [] }
        ]);

        expect(operator.parameters[0].columns).toEqual([]);
    });
});
