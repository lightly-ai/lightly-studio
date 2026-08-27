import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import DatasetDistributionPanel from './DatasetDistributionPanel.svelte';
import { balanced, empty, longTail } from '../BarChart/fixtures';
import type { DistributionSource } from './types';
import { AnnotationCountMode, AnnotationType } from '$lib/api/lightly_studio_local/types.gen';

const echartsMock = vi.hoisted(() => {
    const zrHandlers: Record<string, (event: { offsetX: number; offsetY: number }) => void> = {};
    let clickHandler: ((params: { dataIndex?: number }) => void) | undefined;
    const instance = {
        setOption: vi.fn(),
        resize: vi.fn(),
        dispose: vi.fn(),
        on: vi.fn((event: string, handler: (params: { dataIndex?: number }) => void) => {
            if (event === 'click') clickHandler = handler;
        }),
        // 2 bins across a 200px-wide canvas → 100px per bin index.
        convertFromPixel: vi.fn((_finder: unknown, offsetX: number) => offsetX / 100),
        getZr: () => ({
            on: (event: string, handler: (event: { offsetX: number; offsetY: number }) => void) => {
                zrHandlers[event] = handler;
            },
            off: vi.fn()
        })
    };
    return {
        init: vi.fn(() => instance),
        instance,
        zrHandlers,
        getClickHandler: () => clickHandler
    };
});

vi.mock('echarts/core', () => ({
    init: echartsMock.init,
    use: vi.fn()
}));
vi.mock('echarts/charts', () => ({ BarChart: {}, CustomChart: {} }));
vi.mock('echarts/components', () => ({
    GridComponent: {},
    LegendComponent: {},
    TooltipComponent: {}
}));
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }));

if (typeof globalThis.ResizeObserver === 'undefined') {
    globalThis.ResizeObserver = class {
        observe() {}
        unobserve() {}
        disconnect() {}
    } as unknown as typeof ResizeObserver;
}

const defaultProps = { data: balanced };
const comparisonData = [
    {
        sample_tag_id: 'tag-a',
        sample_tag_name: 'Reviewed',
        counts: [
            { label_name: 'car', count: 2 },
            { label_name: 'dog', count: 0 }
        ]
    },
    {
        sample_tag_id: 'tag-b',
        sample_tag_name: 'Priority',
        counts: [
            { label_name: 'car', count: 1 },
            { label_name: 'dog', count: 5 }
        ]
    }
];

describe('DatasetDistributionPanel', () => {
    beforeAll(() => {
        Element.prototype.scrollIntoView = vi.fn();
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
    });

    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title and the class/annotation summary', () => {
        render(DatasetDistributionPanel, { props: defaultProps });

        expect(screen.getByText('Distribution')).toBeInTheDocument();
        expect(
            screen.getByText('5 classes · sorted by count · 491 annotations')
        ).toBeInTheDocument();
    });

    it('summarizes a top-N subset when there are more classes than topN', () => {
        render(DatasetDistributionPanel, { props: { data: longTail, topN: 10 } });

        expect(screen.getByText(/Top 10 of 30 classes · sorted by count/)).toBeInTheDocument();
    });

    it('omits the summary and shows the chart empty state without data', () => {
        render(DatasetDistributionPanel, { props: { data: empty } });

        expect(screen.queryByText(/classes ·/)).not.toBeInTheDocument();
        expect(screen.getByTestId('bar-chart-empty')).toBeInTheDocument();
    });

    it('passes counts to the chart sorted descending', () => {
        const unsorted = [
            { label: 'car', count: 3 },
            { label: 'person', count: 10 },
            { label: 'dog', count: 7 }
        ];
        render(DatasetDistributionPanel, { props: { data: unsorted } });

        // Horizontal default: categories live on the y-axis.
        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
            grid: { top: number };
        };
        expect(option.yAxis.data).toEqual(['person', 'dog', 'car']);
        expect(option.grid.top).toBe(4);
    });

    it('applies a new top-N from the config dialog', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const input = await waitFor(() => screen.getByTestId('distribution-config-top-n'));
        await fireEvent.input(input, { target: { value: '5' } });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        await waitFor(() =>
            expect(screen.getByText(/Top 5 of 30 classes · sorted by count/)).toBeInTheDocument()
        );
    });

    it('shows all classes via the header quick action, which then hides itself', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail, topN: 10 } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-show-all'));

        await waitFor(() =>
            expect(screen.getByText(/30 classes · sorted by count/)).toBeInTheDocument()
        );
        expect(screen.queryByTestId('dataset-distribution-show-all')).not.toBeInTheDocument();
    });

    it('applies a new top-N from the expanded view and keeps it in sync with the panel', async () => {
        render(DatasetDistributionPanel, { props: { data: longTail } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));
        const configure = await waitFor(() =>
            screen.getByTestId('dataset-distribution-expanded-configure')
        );
        await fireEvent.click(configure);
        const input = await waitFor(() => screen.getByTestId('distribution-config-top-n'));
        await fireEvent.input(input, { target: { value: '5' } });
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        // Both the expanded view's header and the panel header reflect the new config.
        await waitFor(() =>
            expect(screen.getAllByText(/Top 5 of 30 classes · sorted by count/)).toHaveLength(2)
        );
    });

    it('toggles the chart orientation from the header', async () => {
        render(DatasetDistributionPanel, { props: defaultProps });

        // Defaults to horizontal bars (categories on the y-axis) to avoid the
        // initial horizontal scroll.
        expect(
            (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } }).yAxis
                .type
        ).toBe('category');

        await fireEvent.click(screen.getByTestId('dataset-distribution-toggle-orientation'));

        await waitFor(() =>
            expect(
                (echartsMock.instance.setOption.mock.lastCall?.[0] as { yAxis: { type: string } })
                    .yAxis.type
            ).toBe('value')
        );
    });

    it('shows the source selector and switches the charted data between sources', async () => {
        const sources: DistributionSource[] = [
            {
                id: 'class',
                label: 'Class labels',
                data: [{ label: 'car', count: 10 }],
                valueNoun: 'annotations'
            },
            {
                id: 'tags',
                label: 'Tags',
                data: [{ label: 'reviewed', count: 42 }],
                valueNoun: 'samples'
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        // Default source is the first one (class labels).
        expect(screen.getByText(/1 class · sorted by count · 10 annotations/)).toBeInTheDocument();

        // The source selector is present; a single-source panel would not show it.
        expect(screen.getByTestId('dataset-distribution-source-select')).toBeInTheDocument();

        // Horizontal default: categories live on the y-axis.
        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
        };
        expect(option.yAxis.data).toEqual(['car']);
    });

    it('omits the source selector when only one source is available', () => {
        render(DatasetDistributionPanel, { props: defaultProps });
        expect(screen.queryByTestId('dataset-distribution-source-select')).not.toBeInTheDocument();
    });

    it('ranks comparison classes by aggregate counts and keeps tag series independent', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'classes',
                        label: 'Annotation classes',
                        data: [
                            { label: 'car', count: 10 },
                            { label: 'dog', count: 5, selected: true }
                        ],
                        comparisonData
                    }
                ],
                selectedComparisonTagIds: ['tag-a', 'tag-b']
            }
        });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
            series: {
                name: string;
                data: (number | { value: number; itemStyle: { opacity: number } })[];
            }[];
        };
        // dog has the highest aggregate (0+5=5), car second (2+1=3).
        expect(option.yAxis.data).toEqual(['dog', 'car']);
        // Series names are preserved; each tag is independent (not merged).
        expect(option.series).toMatchObject([{ name: 'Reviewed' }, { name: 'Priority' }]);
        expect(option.series[0].data).toEqual([
            { value: 0, itemStyle: { opacity: 1 } },
            { value: 100, itemStyle: { opacity: 0.25 } }
        ]);
        expect(screen.getByText(/2 sample tags/)).toBeInTheDocument();
        expect(screen.queryByText(/annotations/)).not.toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));
        await waitFor(() => expect(screen.getAllByText(/2 sample tags/)).toHaveLength(2));
    });

    it('defaults tag comparisons to percentage and allows switching to numbers', async () => {
        const user = userEvent.setup();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'classes',
                        label: 'Annotation classes',
                        comparisonData
                    }
                ],
                selectedComparisonTagIds: ['tag-a', 'tag-b']
            }
        });

        const valueMode = screen.getByTestId('dataset-distribution-value-mode');
        await waitFor(() => expect(valueMode).toHaveTextContent('Percentage'));

        await user.click(valueMode);
        await user.click(screen.getByRole('option', { name: 'Number' }));
        await waitFor(() => expect(valueMode).toHaveTextContent('Number'));
    });

    it('renders comparison data from the selected annotation-type group', async () => {
        const user = userEvent.setup();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'classes',
                        label: 'Annotation classes',
                        groupLabel: 'Annotation type',
                        groups: [
                            { id: 'all', label: 'All types', data: balanced },
                            {
                                id: 'classification',
                                label: 'Classification',
                                data: [{ label: 'car', count: 3 }],
                                comparisonData
                            }
                        ]
                    }
                ],
                selectedComparisonTagIds: ['tag-a', 'tag-b']
            }
        });

        await user.click(screen.getByTestId('dataset-distribution-group-select'));
        await user.click(screen.getByText('Classification'));

        await waitFor(() => expect(screen.getByText(/2 sample tags/)).toBeInTheDocument());
    });

    it('renders categorical metadata as grouped tag series on a shared value axis', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'metadata',
                        label: 'Metadata',
                        groups: [
                            {
                                id: 'city',
                                label: 'city',
                                categorical: {
                                    buckets: [
                                        {
                                            id: 'zurich',
                                            kind: 'value',
                                            value: 'Zurich',
                                            label: 'Zurich',
                                            count: 10
                                        }
                                    ],
                                    selectedValues: []
                                },
                                comparisonSeries: [
                                    {
                                        id: 'tag-a',
                                        label: 'Reviewed',
                                        data: [{ id: 'zurich', label: 'Zurich', count: 4 }]
                                    },
                                    {
                                        id: 'tag-b',
                                        label: 'Priority',
                                        data: [{ id: 'missing', label: 'Missing', count: 2 }]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                comparisonTagItems: [
                    { value: 'tag-a', label: 'Reviewed' },
                    { value: 'tag-b', label: 'Priority' }
                ],
                selectedComparisonTagIds: ['tag-a', 'tag-b'],
                onComparisonTagIdsChange: vi.fn()
            }
        });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
            series: { name: string }[];
        };
        expect(option.yAxis.data).toEqual(['zurich', 'missing']);
        expect(option.series).toMatchObject([{ name: 'Reviewed' }, { name: 'Priority' }]);
        expect(screen.getByText('Compare by')).toBeInTheDocument();
    });

    const comparisonOnlySources = (
        comparisonBuckets?: {
            id: string;
            kind: 'value';
            value: string;
            label: string;
            count: number;
        }[]
    ): DistributionSource[] => [
        {
            id: 'metadata',
            label: 'Metadata',
            groups: [
                {
                    id: 'city',
                    label: 'city',
                    categorical: {
                        buckets: [
                            {
                                id: 'zurich',
                                kind: 'value',
                                value: 'Zurich',
                                label: 'Zurich',
                                count: 10
                            }
                        ],
                        ...(comparisonBuckets ? { comparisonBuckets } : {}),
                        selectedValues: []
                    },
                    // 'bern' exists only in the tag, never in the current view.
                    comparisonSeries: [
                        {
                            id: 'tag-a',
                            label: 'Reviewed',
                            data: [
                                { id: 'zurich', label: 'Zurich', count: 4 },
                                { id: 'bern', label: 'Bern', count: 6 }
                            ]
                        }
                    ]
                }
            ]
        }
    ];

    const comparisonProps = {
        comparisonTagItems: [{ value: 'tag-a', label: 'Reviewed' }],
        selectedComparisonTagIds: ['tag-a'],
        onComparisonTagIdsChange: vi.fn()
    };

    it('toggles a filter for a value only a comparison tag holds', () => {
        const onCategoricalValueToggle = vi.fn();
        render(DatasetDistributionPanel, {
            props: {
                sources: comparisonOnlySources([
                    { id: 'bern', kind: 'value', value: 'Bern', label: 'Bern', count: 6 }
                ]),
                onCategoricalValueToggle,
                ...comparisonProps
            }
        });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
        };
        // Ranked by aggregate across tags: Bern (6) before Zurich (4).
        expect(option.yAxis.data).toEqual(['bern', 'zurich']);

        echartsMock.getClickHandler()?.({ dataIndex: 0 });
        expect(onCategoricalValueToggle).toHaveBeenCalledWith('city', 'Bern');
    });

    it('leaves a comparison-only bar unclickable when no bucket describes it', () => {
        const onCategoricalValueToggle = vi.fn();
        render(DatasetDistributionPanel, {
            props: {
                sources: comparisonOnlySources(),
                onCategoricalValueToggle,
                ...comparisonProps
            }
        });

        echartsMock.getClickHandler()?.({ dataIndex: 0 });
        expect(onCategoricalValueToggle).not.toHaveBeenCalled();
    });

    it('keeps current-view-only buckets in the shared categorical axis', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'metadata',
                        label: 'Metadata',
                        groups: [
                            {
                                id: 'city',
                                label: 'city',
                                categorical: {
                                    // 'london' has no entry in any comparison tag.
                                    buckets: [
                                        {
                                            id: 'zurich',
                                            kind: 'value',
                                            value: 'Zurich',
                                            label: 'Zurich',
                                            count: 5
                                        },
                                        {
                                            id: 'london',
                                            kind: 'value',
                                            value: 'London',
                                            label: 'London',
                                            count: 3
                                        }
                                    ],
                                    selectedValues: []
                                },
                                comparisonSeries: [
                                    {
                                        id: 'tag-a',
                                        label: 'Reviewed',
                                        data: [{ id: 'zurich', label: 'Zurich', count: 4 }]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                ...comparisonProps
            }
        });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[] };
        };
        expect(option.yAxis.data).toContain('london');
    });

    it('reports a failed tag comparison instead of showing fewer tags silently', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: comparisonOnlySources().map((source) => ({
                    ...source,
                    comparisonLoading: true,
                    comparisonError: 'Request failed'
                })),
                ...comparisonProps
            }
        });

        expect(screen.getByTestId('dataset-distribution-comparison-error')).toBeInTheDocument();
        // The error wins over the in-flight refetch behind it.
        expect(
            screen.queryByTestId('dataset-distribution-comparison-loading')
        ).not.toBeInTheDocument();
    });

    it('marks an in-flight tag comparison so an empty chart is not read as no data', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: comparisonOnlySources().map((source) => ({
                    ...source,
                    comparisonLoading: true
                })),
                ...comparisonProps
            }
        });

        expect(screen.getByTestId('dataset-distribution-comparison-loading')).toBeInTheDocument();
    });

    it('defaults to the first source with content when a leading source is empty', () => {
        const sources: DistributionSource[] = [
            { id: 'all', label: 'All types', data: [], valueNoun: 'annotations' },
            {
                id: 'metadata',
                label: 'Metadata',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        // The empty "All types" source is skipped in favour of metadata.
        expect(screen.getByTestId('histogram')).toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples · 2 bins · 0–1'
        );
    });

    it('preserves categorical endpoint order and toggles typed buckets but not Other', () => {
        const onCategoricalValueToggle = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: ['Missing'],
                            buckets: [
                                {
                                    id: 'literal',
                                    kind: 'value',
                                    value: 'Missing',
                                    label: 'Missing',
                                    count: 4
                                },
                                {
                                    id: 'missing',
                                    kind: 'missing',
                                    value: null,
                                    label: 'Missing',
                                    count: 3
                                },
                                { id: 'other', kind: 'other', label: 'Other', count: 2 }
                            ]
                        }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources, onCategoricalValueToggle } });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[]; axisLabel: { formatter: (key: string) => string } };
            series: [{ data: { itemStyle: { color: string } }[] }];
            grid: { top: number };
        };
        expect(option.yAxis.data).toEqual(['literal', 'missing', 'other']);
        expect(option.yAxis.data.map(option.yAxis.axisLabel.formatter)).toEqual([
            'Missing',
            'Missing',
            'Other'
        ]);
        expect(option.grid.top).toBe(4);
        // 'Missing' (value) is selected → accent green; the others are dimmed grey.
        expect(option.series[0].data[0].itemStyle.color).toBe('rgba(59,217,159,0.85)');

        echartsMock.getClickHandler()?.({ dataIndex: 1 });
        expect(onCategoricalValueToggle).toHaveBeenCalledWith('city', null);
        echartsMock.getClickHandler()?.({ dataIndex: 2 });
        expect(onCategoricalValueToggle).toHaveBeenCalledOnce();
    });

    it('stores categorical orientation per metadata field', async () => {
        const user = userEvent.setup();
        const categorical = (label: string) => ({
            selectedValues: [],
            buckets: [{ id: label, kind: 'value' as const, value: label, label, count: 1 }]
        });
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groupLabel: 'Metadata key',
                groups: [
                    { id: 'city', label: 'city', categorical: categorical('Zurich') },
                    { id: 'weather', label: 'weather', categorical: categorical('rainy') }
                ]
            },
            { id: 'classes', label: 'Classes', data: [] }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        const orientationToggle = screen.getByTestId('dataset-distribution-toggle-orientation');
        await fireEvent.click(orientationToggle);
        expect(orientationToggle).toHaveAccessibleName('Switch to horizontal bars');

        const groupSelect = screen.getByTestId('dataset-distribution-group-select');
        await user.click(groupSelect);
        await user.click(await screen.findByRole('option', { name: 'weather' }));
        expect(orientationToggle).toHaveAccessibleName('Switch to vertical bars');

        await user.click(groupSelect);
        await user.click(await screen.findByRole('option', { name: 'city' }));
        expect(orientationToggle).toHaveAccessibleName('Switch to horizontal bars');
    });

    it('configures, reorients, and expands categorical values', async () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: [],
                            buckets: [
                                {
                                    id: 'zurich',
                                    kind: 'value',
                                    value: 'Zurich',
                                    label: 'Zurich',
                                    count: 4
                                },
                                {
                                    id: 'missing',
                                    kind: 'missing',
                                    value: null,
                                    label: 'Missing',
                                    count: 1
                                }
                            ]
                        }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByText(/2 values · sorted by count · 5 samples/)).toBeInTheDocument();
        const orientationToggle = screen.getByTestId('dataset-distribution-toggle-orientation');
        expect(orientationToggle).toHaveAccessibleName('Switch to vertical bars');

        await fireEvent.click(orientationToggle);
        await waitFor(() =>
            expect(
                (echartsMock.instance.setOption.mock.lastCall?.[0] as { xAxis: { type: string } })
                    .xAxis.type
            ).toBe('category')
        );
        expect(orientationToggle).toHaveAccessibleName('Switch to horizontal bars');

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        expect(screen.getByText('Configure values')).toBeInTheDocument();
        expect(screen.queryByTestId('distribution-config-count-mode')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByText('Cancel'));

        await fireEvent.click(screen.getByTestId('dataset-distribution-expand'));
        expect(screen.getByTestId('dataset-distribution-expanded-configure')).toBeInTheDocument();
        const expandedOrientationToggle = screen.getByTestId(
            'dataset-distribution-expanded-toggle-orientation'
        );
        expect(expandedOrientationToggle).toHaveAccessibleName('Switch to horizontal bars');

        await fireEvent.click(expandedOrientationToggle);
        await waitFor(() =>
            expect(orientationToggle).toHaveAccessibleName('Switch to vertical bars')
        );
    });

    it('manually configures colliding categorical labels by stable bucket id', async () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'status',
                        label: 'status',
                        categorical: {
                            selectedValues: [],
                            buckets: [
                                {
                                    id: 'literal-missing',
                                    kind: 'value',
                                    value: 'Missing',
                                    label: 'Missing',
                                    count: 4
                                },
                                {
                                    id: 'semantic-missing',
                                    kind: 'missing',
                                    value: null,
                                    label: 'Missing',
                                    count: 3
                                }
                            ]
                        }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        await fireEvent.click(screen.getByRole('tab', { name: 'Manual' }));
        const missingOptions = screen.getAllByText('Missing');
        expect(missingOptions).toHaveLength(2);
        await fireEvent.click(missingOptions[1]);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            yAxis: { data: string[]; axisLabel: { formatter: (key: string) => string } };
            series: [{ data: { value: number }[] }];
        };
        expect(option.yAxis.data).toEqual(['semantic-missing']);
        expect(option.yAxis.axisLabel.formatter('semantic-missing')).toBe('Missing');
        expect(option.series[0].data[0].value).toBe(3);
    });

    it('shows categorical loading and retryable error states', async () => {
        const onCategoricalRetry = vi.fn();
        const source = (state: { loading?: boolean; error?: string }): DistributionSource[] => [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: { buckets: [], selectedValues: ['Zurich'], ...state }
                    }
                ]
            }
        ];
        const view = render(DatasetDistributionPanel, {
            props: { sources: source({ loading: true }), onCategoricalRetry }
        });
        expect(screen.getByRole('status')).toHaveTextContent('Loading metadata distribution');

        await view.rerender({
            sources: source({ error: 'network failure' }),
            onCategoricalRetry
        });
        expect(screen.getByRole('alert')).toHaveTextContent('Could not load metadata distribution');
        await fireEvent.click(screen.getByTestId('metadata-categorical-retry'));
        expect(onCategoricalRetry).toHaveBeenCalledOnce();
    });

    it('keeps stale categorical bars visible after a refetch error', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            buckets: [
                                {
                                    id: 'zurich',
                                    kind: 'value',
                                    value: 'Zurich',
                                    label: 'Zurich',
                                    count: 4
                                }
                            ],
                            selectedValues: [],
                            error: 'network failure'
                        }
                    }
                ]
            }
        ];

        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByRole('alert')).toHaveTextContent('Could not update');
        expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
        expect(screen.getByLabelText('Categorical metadata value counts')).toHaveTextContent(
            'Zurich: 4 samples'
        );
    });

    it('renders a close button only when onClose is provided and forwards clicks', async () => {
        const onClose = vi.fn();
        render(DatasetDistributionPanel, { props: { ...defaultProps, onClose } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-close-button'));

        expect(onClose).toHaveBeenCalledOnce();
    });

    it('shows the count by select in the config dialog with Objects selected by default', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ]
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));

        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        expect(countBySelect).toBeInTheDocument();
        expect(countBySelect).toHaveTextContent('Objects');
    });

    it('shows the count by select for All types source too', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'all',
                        label: 'All types',
                        data: [{ label: 'car', count: 5 }]
                    },
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ]
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));

        await waitFor(() =>
            expect(screen.getByTestId('distribution-config-count-mode')).toBeInTheDocument()
        );
    });

    it('calls onCountModeChange when count mode changes via the config dialog', async () => {
        const user = userEvent.setup();
        const onCountModeChange = vi.fn();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 5 }]
                    }
                ],
                onCountModeChange
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        await user.click(countBySelect);
        const samplesOption = await waitFor(() => screen.getByRole('option', { name: 'Samples' }));
        await user.click(samplesOption);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        expect(onCountModeChange).toHaveBeenCalledWith(AnnotationCountMode.SAMPLES);
    });

    it('hides the total count in the header when count mode is changed to Samples', async () => {
        const user = userEvent.setup();
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 10 }],
                        valueNoun: 'instances'
                    }
                ]
            }
        });

        expect(screen.getByText(/10 instances/)).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('dataset-distribution-configure'));
        const countBySelect = await waitFor(() =>
            screen.getByTestId('distribution-config-count-mode')
        );
        await user.click(countBySelect);
        const samplesOption = await waitFor(() => screen.getByRole('option', { name: 'Samples' }));
        await user.click(samplesOption);
        await fireEvent.click(screen.getByTestId('distribution-config-apply'));

        await waitFor(() => expect(screen.queryByText(/instances/)).not.toBeInTheDocument());
    });

    it('shows the total count in the header by default (Objects mode)', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: AnnotationType.OBJECT_DETECTION,
                        label: 'Object detection',
                        data: [{ label: 'car', count: 10 }],
                        valueNoun: 'instances'
                    }
                ]
            }
        });

        expect(screen.getByText(/10 instances/)).toBeInTheDocument();
    });

    it('renders a histogram instead of a bar chart for a group carrying bins', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groupLabel: 'Metadata key',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByTestId('histogram')).toBeInTheDocument();
        expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
        // Categorical controls (sort / top-N / orientation) don't apply to bins.
        expect(screen.queryByText(/sorted by/)).not.toBeInTheDocument();
    });

    it('summarizes a histogram group with total count, bins and range', () => {
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources } });

        expect(screen.getByTestId('dataset-distribution-histogram-summary')).toHaveTextContent(
            '100 samples · 2 bins · 0–1'
        );
    });

    it('forwards a histogram range selection as the group id and value interval', () => {
        const onHistogramRangeSelect = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'metadata',
                label: 'Metadata',
                groupLabel: 'Metadata key',
                valueNoun: 'samples',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, { props: { sources, onHistogramRangeSelect } });

        // Press and release over the second bin (offsetX 150 → index 1.5 → bin 1).
        echartsMock.zrHandlers.mousedown({ offsetX: 150, offsetY: 10 });
        window.dispatchEvent(new MouseEvent('mouseup'));

        expect(onHistogramRangeSelect).toHaveBeenCalledWith('confidence', { min: 0.5, max: 1 });
    });

    it('shows a group selector when the only source has multiple groups', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: [
                    {
                        id: 'classes',
                        label: 'Annotation classes',
                        groups: [
                            { id: 'all', label: 'All types', data: balanced },
                            { id: 'classification', label: 'Classification', data: balanced }
                        ]
                    }
                ]
            }
        });

        expect(screen.queryByTestId('dataset-distribution-source-select')).not.toBeInTheDocument();
        expect(screen.getByTestId('dataset-distribution-group-select')).toBeInTheDocument();
    });

    const histogramSources: DistributionSource[] = [
        {
            id: 'metadata',
            label: 'Metadata',
            groupLabel: 'Metadata key',
            valueNoun: 'samples',
            groups: [
                {
                    id: 'confidence',
                    label: 'confidence',
                    histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                }
            ]
        }
    ];

    it('renders numerical metadata as comparable histogram tag series', () => {
        const sources: DistributionSource[] = [
            {
                ...histogramSources[0],
                groups: [
                    {
                        ...histogramSources[0].groups![0],
                        histogramSeries: [
                            {
                                id: 'tag-a',
                                label: 'Reviewed',
                                data: { binEdges: [0, 0.5, 1], counts: [4, 2] }
                            },
                            {
                                id: 'tag-b',
                                label: 'Priority',
                                data: { binEdges: [0, 0.5, 1], counts: [1, 5] }
                            }
                        ]
                    }
                ]
            }
        ];
        render(DatasetDistributionPanel, {
            props: {
                sources,
                comparisonTagItems: [
                    { value: 'tag-a', label: 'Reviewed' },
                    { value: 'tag-b', label: 'Priority' }
                ],
                selectedComparisonTagIds: ['tag-a', 'tag-b'],
                onComparisonTagIdsChange: vi.fn()
            }
        });

        const option = echartsMock.instance.setOption.mock.lastCall?.[0] as {
            xAxis: { max: number };
            series: { name: string; data: { value: [number, number] }[] }[];
        };
        expect(option.xAxis.max).toBe(2);
        expect(option.series).toMatchObject([{ name: 'Reviewed' }, { name: 'Priority' }]);
        expect(option.series[0].data.map(({ value }) => value)).toEqual([
            [0.5, 4],
            [1.5, 2]
        ]);
    });

    it('shows the bin-count select only when a change handler is provided', () => {
        render(DatasetDistributionPanel, { props: { sources: histogramSources } });
        expect(screen.queryByTestId('dataset-distribution-bin-count')).not.toBeInTheDocument();
    });

    it('renders the bin-count select with the applied bin count', () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: histogramSources,
                histogramBinCount: 50,
                onHistogramBinCountChange: vi.fn()
            }
        });

        expect(screen.getByTestId('dataset-distribution-bin-count')).toHaveTextContent('50 bins');
    });

    it('expands the histogram into a dialog with the same data', async () => {
        render(DatasetDistributionPanel, { props: { sources: histogramSources } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-histogram-expand'));

        // Panel + expanded dialog each render a histogram.
        await waitFor(() => expect(screen.getAllByTestId('histogram')).toHaveLength(2));
        expect(
            screen.getByTestId('dataset-distribution-expanded-histogram-summary')
        ).toHaveTextContent('100 samples · 2 bins · 0–1');
    });

    it('hides the bin-count select in the expanded dialog when no change handler is provided', async () => {
        render(DatasetDistributionPanel, { props: { sources: histogramSources } });

        await fireEvent.click(screen.getByTestId('dataset-distribution-histogram-expand'));

        await waitFor(() => expect(screen.getAllByTestId('histogram')).toHaveLength(2));
        expect(
            screen.queryByTestId('dataset-distribution-expanded-bin-count')
        ).not.toBeInTheDocument();
    });

    it('shows the bin-count select in the expanded dialog with the applied bin count', async () => {
        render(DatasetDistributionPanel, {
            props: {
                sources: histogramSources,
                histogramBinCount: 50,
                onHistogramBinCountChange: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('dataset-distribution-histogram-expand'));

        await waitFor(() =>
            expect(screen.getByTestId('dataset-distribution-expanded-bin-count')).toHaveTextContent(
                '50 bins'
            )
        );
    });

    it('calls onHistogramBinCountChange with the selected count when the user picks a new value', async () => {
        const onHistogramBinCountChange = vi.fn();
        const user = userEvent.setup();
        render(DatasetDistributionPanel, {
            props: {
                sources: histogramSources,
                histogramBinCount: 20,
                onHistogramBinCountChange
            }
        });

        await user.click(screen.getByTestId('dataset-distribution-bin-count'));
        const option = await waitFor(() => screen.getByRole('option', { name: '10 bins' }));
        await user.click(option);

        expect(onHistogramBinCountChange).toHaveBeenCalledWith(10);
    });
});
