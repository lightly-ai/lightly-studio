import type { BaseParameter, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';

export type OperatorParameterType = 'string' | 'int' | 'float' | 'bool';

export type OperatorScope =
    | 'root'
    | 'image'
    | 'video_frame'
    | 'video';

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
    supportedScopes: OperatorScope[];
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
    parameters: parameters.map(mapParameter),
    supportedScopes: (metadata.supported_scopes ?? []) as OperatorScope[]
});
