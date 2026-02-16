import type { BaseParameter, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';

export type OperatorParameterType = 'string' | 'int' | 'float' | 'bool';

export type OperatorParameter = {
    name: string;
    description?: string;
    default?: unknown;
    required?: boolean;
    type: OperatorParameterType;
};

export type Operator = {
    id: string;
    name: string;
    status: string;
    parameters: OperatorParameter[];
};

const mapParameter = (parameter: BaseParameter): OperatorParameter => ({
    name: parameter.name,
    description: parameter.description,
    default: parameter.default,
    required: parameter.required,
    type: (parameter.param_type as OperatorParameterType) ?? 'string'
});

export const createOperatorFromMetadata = (
    metadata: RegisteredOperatorMetadata,
    parameters: BaseParameter[]
): Operator => ({
    id: metadata.operator_id,
    name: metadata.name,
    status: metadata.status,
    parameters: parameters.map(mapParameter)
});
