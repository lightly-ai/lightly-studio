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
    parameters: OperatorParameter[];
};

const normalizeParameterType = (paramType?: string | null): OperatorParameterType => {
    const normalized = paramType?.toLowerCase();
    switch (normalized) {
        case 'bool':
        case 'boolean':
            return 'bool';
        case 'int':
        case 'integer':
            return 'int';
        case 'float':
        case 'double':
            return 'float';
        default:
            return 'string';
    }
};

const mapParameter = (parameter: BaseParameter): OperatorParameter => ({
    name: parameter.name,
    description: parameter.description,
    default: parameter.default,
    required: parameter.required,
    type: normalizeParameterType(parameter.param_type)
});

export const createOperatorFromMetadata = (
    metadata: RegisteredOperatorMetadata,
    parameters: BaseParameter[]
): Operator => ({
    id: metadata.operator_id,
    name: metadata.name,
    parameters: parameters.map(mapParameter)
});
