import { describe, expect, it, vi } from 'vitest';
import {
    useDistributionPanel,
    type UseDistributionPanelParams
} from './useDistributionPanel.svelte';
import type { DistributionSource } from './types';
import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';

const renderHook = (props: UseDistributionPanelParams = {}) => useDistributionPanel(() => props);

describe('useDistributionPanel', () => {
    it('normalizes data to a single source when sources is not provided', () => {
        const data = [{ label: 'car', count: 10 }];
        const panel = renderHook({ data });

        expect(panel.activeSource.id).toBe('class');
        expect(panel.activeData).toEqual(data);
    });

    it('defaults to the first source with content, skipping empty leading sources', () => {
        const sources: DistributionSource[] = [
            { id: 'empty', label: 'Empty', data: [] },
            { id: 'full', label: 'Full', data: [{ label: 'car', count: 5 }] }
        ];
        const panel = renderHook({ sources });

        expect(panel.activeSource.id).toBe('full');
    });

    it('defaults to a source with a histogram when the first source has no bar data', () => {
        const sources: DistributionSource[] = [
            { id: 'all', label: 'All', data: [] },
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    { id: 'conf', label: 'conf', histogram: { binEdges: [0, 1], counts: [10] } }
                ]
            }
        ];
        const panel = renderHook({ sources });

        expect(panel.activeSource.id).toBe('meta');
        expect(panel.activeHistogram).not.toBeNull();
    });

    it('changes active source via setSelectedSourceId', () => {
        const sources: DistributionSource[] = [
            { id: 'a', label: 'A', data: [{ label: 'x', count: 1 }] },
            { id: 'b', label: 'B', data: [{ label: 'y', count: 2 }] }
        ];
        const panel = renderHook({ sources });

        panel.setSelectedSourceId('b');

        expect(panel.activeSource.id).toBe('b');
        expect(panel.activeData).toEqual([{ label: 'y', count: 2 }]);
    });

    it('changes active group via setSelectedGroupId', () => {
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'g1',
                        label: 'G1',
                        categorical: {
                            selectedValues: [],
                            buckets: [{ id: 'a', kind: 'value', value: 'A', label: 'A', count: 1 }]
                        }
                    },
                    {
                        id: 'g2',
                        label: 'G2',
                        categorical: {
                            selectedValues: [],
                            buckets: [{ id: 'b', kind: 'value', value: 'B', label: 'B', count: 2 }]
                        }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources });
        expect(panel.activeGroup?.id).toBe('g1');

        panel.setSelectedGroupId('g2');

        expect(panel.activeGroup?.id).toBe('g2');
    });

    it('maps categorical buckets to CategoryCount with correct selection and pin flags', () => {
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: ['Zurich'],
                            buckets: [
                                {
                                    id: 'z',
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
                                    count: 2
                                },
                                { id: 'other', kind: 'other', label: 'Other', count: 1 }
                            ]
                        }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources });

        expect(panel.categoricalData).toEqual([
            expect.objectContaining({ id: 'z', selected: true, selectable: true, pinned: false }),
            expect.objectContaining({
                id: 'missing',
                selected: false,
                selectable: true,
                pinned: true
            }),
            expect.objectContaining({
                id: 'other',
                selected: false,
                selectable: false,
                pinned: true
            })
        ]);
    });

    it('applyConfig updates config and fires onCountModeChange when mode changes', () => {
        const onCountModeChange = vi.fn();
        const panel = renderHook({ data: [{ label: 'car', count: 5 }], onCountModeChange });

        panel.applyConfig({ ...panel.config, countMode: AnnotationCountMode.SAMPLES });

        expect(onCountModeChange).toHaveBeenCalledWith(AnnotationCountMode.SAMPLES);
        expect(panel.config.countMode).toBe(AnnotationCountMode.SAMPLES);
    });

    it('applyConfig does not fire onCountModeChange when mode is unchanged', () => {
        const onCountModeChange = vi.fn();
        const panel = renderHook({ data: [{ label: 'car', count: 5 }], onCountModeChange });

        panel.applyConfig({ ...panel.config, n: 5 });

        expect(onCountModeChange).not.toHaveBeenCalled();
    });

    it('applyConfig routes to setCategoricalConfig for categorical sources', () => {
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: [],
                            buckets: [{ id: 'z', kind: 'value', value: 'Z', label: 'Z', count: 4 }]
                        }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources });

        panel.applyConfig({ ...panel.categoricalConfig, n: 5 });

        expect(panel.categoricalConfig.n).toBe(5);
        expect(panel.categoricalConfig.countMode).toBe(AnnotationCountMode.SAMPLES);
    });

    it('setCategoricalConfig stores config per group independently', () => {
        const makeCategorical = (label: string) => ({
            selectedValues: [] as string[],
            buckets: [{ id: label, kind: 'value' as const, value: label, label, count: 1 }]
        });
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    { id: 'city', label: 'city', categorical: makeCategorical('Zurich') },
                    { id: 'weather', label: 'weather', categorical: makeCategorical('rainy') }
                ]
            }
        ];
        const panel = renderHook({ sources });

        panel.setCategoricalConfig({ ...panel.categoricalConfig, n: 3 });
        expect(panel.categoricalConfig.n).toBe(3);

        panel.setSelectedGroupId('weather');
        expect(panel.categoricalConfig.n).toBe(1);

        panel.setSelectedGroupId('city');
        expect(panel.categoricalConfig.n).toBe(3);
    });

    it('handleHistogramRangeSelect forwards the range with the active group id', () => {
        const onHistogramRangeSelect = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'confidence',
                        label: 'confidence',
                        histogram: { binEdges: [0, 0.5, 1], counts: [30, 70] }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources, onHistogramRangeSelect });

        panel.handleHistogramRangeSelect({ min: 0.5, max: 1 });

        expect(onHistogramRangeSelect).toHaveBeenCalledWith('confidence', { min: 0.5, max: 1 });
    });

    it('handleCategoricalBarClick forwards value/missing bucket clicks but ignores other', () => {
        const onCategoricalValueToggle = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: [],
                            buckets: [
                                {
                                    id: 'z',
                                    kind: 'value',
                                    value: 'Zurich',
                                    label: 'Zurich',
                                    count: 4
                                },
                                { id: 'other', kind: 'other', label: 'Other', count: 1 }
                            ]
                        }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources, onCategoricalValueToggle });

        panel.handleCategoricalBarClick({ id: 'z', label: 'Zurich', count: 4 });
        expect(onCategoricalValueToggle).toHaveBeenCalledWith('city', 'Zurich');

        panel.handleCategoricalBarClick({ id: 'other', label: 'Other', count: 1 });
        expect(onCategoricalValueToggle).toHaveBeenCalledOnce();
    });

    it('handleCategoricalFilterToggle and handleCategoricalFilterClear use the active group id', () => {
        const onCategoricalValueToggle = vi.fn();
        const onCategoricalValuesClear = vi.fn();
        const sources: DistributionSource[] = [
            {
                id: 'meta',
                label: 'Meta',
                groups: [
                    {
                        id: 'city',
                        label: 'city',
                        categorical: {
                            selectedValues: [],
                            buckets: [
                                {
                                    id: 'z',
                                    kind: 'value',
                                    value: 'Zurich',
                                    label: 'Zurich',
                                    count: 4
                                }
                            ]
                        }
                    }
                ]
            }
        ];
        const panel = renderHook({ sources, onCategoricalValueToggle, onCategoricalValuesClear });

        panel.handleCategoricalFilterToggle('Zurich');
        expect(onCategoricalValueToggle).toHaveBeenCalledWith('city', 'Zurich');

        panel.handleCategoricalFilterClear();
        expect(onCategoricalValuesClear).toHaveBeenCalledWith('city');
    });

    it('showTotalCount is true for Objects mode and false for Samples mode', () => {
        const panel = renderHook({ data: [{ label: 'car', count: 5 }] });
        expect(panel.showTotalCount).toBe(true);

        panel.applyConfig({ ...panel.config, countMode: AnnotationCountMode.SAMPLES });
        expect(panel.showTotalCount).toBe(false);
    });
});
