import type { ParameterView, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';

export type OperatorParameterType = 'string' | 'int' | 'float' | 'bool';

/**
 * A single column of a table parameter as consumed by the GUI.
 */
export type OperatorParameterColumn = {
    name: string;
    description?: string;
    default?: unknown;
    required?: boolean;
    /** Python type name, e.g. `'str'`, `'int'`, `'float'` or `'bool'`. */
    paramType?: string;
};

export type OperatorParameter = {
    name: string;
    description?: string;
    default?: unknown;
    required?: boolean;
    type: OperatorParameterType;
    columns?: OperatorParameterColumn[];
};

export type Operator = {
    id: string;
    name: string;
    parameters: OperatorParameter[];
};

const mapParameter = (parameter: ParameterView): OperatorParameter => ({
    name: parameter.name,
    description: parameter.description,
    default: parameter.default,
    required: parameter.required,
    type: (parameter.param_type as OperatorParameterType) ?? 'string'
});

export const createOperatorFromMetadata = (
    metadata: RegisteredOperatorMetadata,
    parameters: ParameterView[]
): Operator => ({
    id: metadata.operator_id,
    name: metadata.name,
    parameters: parameters.map(mapParameter)
});
