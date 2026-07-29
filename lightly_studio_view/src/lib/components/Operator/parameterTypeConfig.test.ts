import { describe, expect, it } from 'vitest';
import type { ParameterView, RegisteredOperatorMetadata } from '$lib/api/lightly_studio_local';
import type { Operator } from '$lib/hooks/useOperators/useOperators';
import { createOperatorFromMetadata } from '$lib/hooks/useOperators/useOperators';
import ParameterTable from './ParameterTable.svelte';
import { buildInitialParameters, getParameterConfig, isValueFilled } from './parameterTypeConfig';

const COLUMNS = [
    { name: 'prompt', required: true },
    { name: 'label', required: true }
];

describe('isValueFilled', () => {
    it('rejects an empty table', () => {
        expect(isValueFilled([], 'table', COLUMNS)).toBe(false);
    });

    it('rejects a table with a blank or whitespace-only cell', () => {
        expect(isValueFilled([{ prompt: 'person', label: '' }], 'table', COLUMNS)).toBe(false);
        expect(isValueFilled([{ prompt: 'person', label: '   ' }], 'table', COLUMNS)).toBe(false);
    });

    it('rejects a table where only some rows are complete', () => {
        expect(
            isValueFilled(
                [
                    { prompt: 'person', label: 'pedestrian' },
                    { prompt: 'car', label: '' }
                ],
                'table',
                COLUMNS
            )
        ).toBe(false);
    });

    it('accepts a table where every cell of every row is filled', () => {
        expect(
            isValueFilled(
                [
                    { prompt: 'person', label: 'pedestrian' },
                    { prompt: 'car', label: 'vehicle' }
                ],
                'table',
                COLUMNS
            )
        ).toBe(true);
    });

    it('accepts a table with an empty cell in a column that is not required', () => {
        const columns = [
            { name: 'prompt', required: true },
            { name: 'label', required: false }
        ];

        expect(isValueFilled([{ prompt: 'person', label: '' }], 'table', columns)).toBe(true);
        expect(isValueFilled([{ prompt: '', label: 'pedestrian' }], 'table', columns)).toBe(false);
    });

    it('treats every cell as required when no columns are known', () => {
        expect(isValueFilled([{ prompt: 'person', label: '' }], 'table')).toBe(false);
        expect(isValueFilled([{ prompt: 'person', label: 'pedestrian' }], 'table')).toBe(true);
    });
});

describe('buildInitialParameters', () => {
    it('clones table rows so the default from the API is not shared', () => {
        const defaultRows = [{ prompt: 'person', label: 'pedestrian' }];
        const operator: Operator = {
            id: 'op-1',
            name: 'SAM3',
            parameters: [
                {
                    name: 'prompts',
                    type: 'table',
                    default: defaultRows,
                    required: true,
                    columns: COLUMNS
                }
            ]
        };

        const initial = buildInitialParameters(operator);

        expect(initial.prompts).toEqual(defaultRows);
        expect(initial.prompts).not.toBe(defaultRows);
        expect((initial.prompts as Record<string, string>[])[0]).not.toBe(defaultRows[0]);
    });

    it('maps a table parameter straight from the API payload to a rendered table', () => {
        // Literal response of GET /operators/{id}/parameters, pinned by the backend test
        // `test_get_operator_parameters__table_parameter`. Guards the backend/frontend seam.
        const apiParameters: ParameterView[] = [
            {
                name: 'prompts',
                description: 'Prompts and labels.',
                default: [{ prompt: 'person', label: 'pedestrian' }],
                required: true,
                param_type: 'table',
                columns: [
                    {
                        name: 'prompt',
                        description: 'What to segment.',
                        default: null,
                        required: true,
                        param_type: 'str'
                    },
                    {
                        name: 'label',
                        description: '',
                        default: 'pedestrian',
                        required: false,
                        param_type: 'str'
                    }
                ]
            }
        ];
        const metadata = {
            operator_id: 'op-1',
            name: 'SAM3 Segmentation',
            supported_scopes: []
        } as RegisteredOperatorMetadata;

        const operator = createOperatorFromMetadata(metadata, apiParameters);

        expect(operator.parameters[0].type).toBe('table');
        expect(operator.parameters[0].columns).toEqual([
            { name: 'prompt', description: 'What to segment.', default: undefined, required: true },
            { name: 'label', description: '', default: 'pedestrian', required: false }
        ]);
        expect(getParameterConfig('table').component).toBe(ParameterTable);
        expect(buildInitialParameters(operator).prompts).toEqual([
            { prompt: 'person', label: 'pedestrian' }
        ]);
    });

    it('falls back to an empty table when a table parameter has no default', () => {
        const operator: Operator = {
            id: 'op-1',
            name: 'SAM3',
            parameters: [
                {
                    name: 'prompts',
                    type: 'table',
                    default: null,
                    required: true,
                    columns: COLUMNS
                }
            ]
        };

        const initial = buildInitialParameters(operator);

        expect(initial.prompts).toEqual([]);
    });
});
