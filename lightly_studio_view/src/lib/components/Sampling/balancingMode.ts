export type BalancingMode = 'uniform' | 'input' | 'dictionary';

export const BALANCING_MODE_LABELS: Record<BalancingMode, string> = {
    uniform: 'Uniform',
    input: 'Input',
    dictionary: 'Custom Dictionary'
};
