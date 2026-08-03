import { type SelectItem } from '$lib/components/Select';
import { type CategoryCount } from '$lib/components/BarChart';
import { type HistogramRange } from '$lib/components/Histogram';
import {
    HISTOGRAM_BIN_COUNT_ITEMS,
    type DistributionConfig,
    type DistributionSource,
    type DistributionSourceGroup
} from './types';
import { AnnotationCountMode } from '$lib/api/lightly_studio_local/types.gen';
import { selectVisibleCounts } from './selectVisibleCounts';
import type { CategoricalMetadataValue } from '$lib/services/types';

export interface UseDistributionPanelParams {
    sources?: DistributionSource[];
    data?: CategoryCount[];
    topN?: number;
    initialCountMode?: AnnotationCountMode;
    onCountModeChange?: (mode: AnnotationCountMode) => void;
    onHistogramRangeSelect?: (groupId: string, range: HistogramRange) => void;
    onCategoricalValueToggle?: (groupId: string, value: CategoricalMetadataValue) => void;
    onCategoricalValuesClear?: (groupId: string) => void;
}

function makeGetters<T extends Record<string, unknown>>(fns: { [K in keyof T]: () => T[K] }): T {
    const result = {} as T;
    for (const key in fns) {
        Object.defineProperty(result, key, { get: fns[key], enumerable: true, configurable: true });
    }
    return result;
}

const defaultCategoricalConfig: DistributionConfig = {
    mode: 'topN',
    n: 1,
    sortBy: 'count',
    manualClasses: [],
    orientation: 'horizontal',
    countMode: AnnotationCountMode.SAMPLES
};

export function useDistributionPanel(getProps: () => UseDistributionPanelParams) {
    const groupHasContent = (group: DistributionSourceGroup): boolean =>
        (group.data?.length ?? 0) > 0 || group.histogram != null || group.categorical != null;

    const sourceHasContent = (source: DistributionSource): boolean =>
        (source.data?.length ?? 0) > 0 ||
        source.histogram != null ||
        (source.groups?.some(groupHasContent) ?? false);

    let selectedSourceId = $state<string | undefined>(undefined);
    let selectedGroupId = $state<string | undefined>(undefined);

    const resolvedSources = $derived<DistributionSource[]>(
        getProps().sources ?? [
            { id: 'class', label: 'Annotation classes', data: getProps().data ?? [] }
        ]
    );
    const hasSourceSelector = $derived(resolvedSources.length > 1);

    const defaultSource = $derived(resolvedSources.find(sourceHasContent) ?? resolvedSources[0]);
    const activeSource = $derived(
        resolvedSources.find((source) => source.id === selectedSourceId) ?? defaultSource
    );
    const activeGroup = $derived(
        activeSource.groups?.find((group) => group.id === selectedGroupId) ??
            activeSource.groups?.find(groupHasContent) ??
            activeSource.groups?.[0]
    );
    const activeData = $derived<CategoryCount[]>(activeGroup?.data ?? activeSource.data ?? []);
    const activeHistogram = $derived(activeGroup?.histogram ?? activeSource.histogram ?? null);
    const activeCategorical = $derived(activeGroup?.categorical ?? null);
    const categoricalData = $derived<CategoryCount[]>(
        (activeCategorical?.buckets ?? []).map((bucket) => {
            const filteredBucket = activeCategorical?.filteredBuckets?.find(
                (fb) => fb.id === bucket.id
            );
            const filteredCount =
                activeCategorical?.filteredBuckets !== undefined
                    ? (filteredBucket?.count ?? 0)
                    : undefined;
            return {
                id: bucket.id,
                label: bucket.label,
                count: bucket.count,
                filteredCount,
                selectable: bucket.kind !== 'other',
                pinned: bucket.kind !== 'value',
                selected:
                    bucket.kind !== 'other' &&
                    activeCategorical?.selectedValues.some((value) =>
                        Object.is(value, bucket.value)
                    )
            };
        })
    );
    const displayedData = $derived(activeCategorical ? categoricalData : activeData);
    const configurationItems = $derived(
        displayedData.map((item) => ({ value: item.id ?? item.label, label: item.label }))
    );
    const activeHistogramRange = $derived(activeGroup?.selectedRange ?? activeSource.selectedRange);
    const histogramTotal = $derived(
        activeHistogram ? activeHistogram.counts.reduce((sum, count) => sum + count, 0) : 0
    );
    const valueNoun = $derived(activeSource.valueNoun ?? 'annotations');

    let config: DistributionConfig = $state({
        mode: 'topN',
        n: getProps().topN ?? 20,
        sortBy: 'count',
        manualClasses: [],
        orientation: 'horizontal',
        countMode: getProps().initialCountMode ?? AnnotationCountMode.OBJECTS
    });
    let categoricalConfigs = $state<Record<string, DistributionConfig>>({});
    const categoricalConfig = $derived<DistributionConfig>(
        activeGroup
            ? (categoricalConfigs[activeGroup.id] ?? {
                  ...defaultCategoricalConfig,
                  n: Math.max(categoricalData.length, 1)
              })
            : defaultCategoricalConfig
    );

    const sourceItems = $derived<SelectItem[]>(
        resolvedSources.map((source) => ({ value: source.id, label: source.label }))
    );
    const groupItems = $derived<SelectItem[]>(
        (activeSource.groups ?? []).map((group) => ({ value: group.id, label: group.label }))
    );

    const activeViewConfig = $derived<DistributionConfig>(
        activeCategorical ? categoricalConfig : config
    );
    const visible = $derived(selectVisibleCounts(displayedData, activeViewConfig));
    const totalCount = $derived(displayedData.reduce((sum, item) => sum + item.count, 0));
    const showTotalCount = $derived(
        (config.countMode ?? AnnotationCountMode.OBJECTS) !== AnnotationCountMode.SAMPLES
    );

    const binCountItems: SelectItem[] = HISTOGRAM_BIN_COUNT_ITEMS.map((count) => ({
        value: String(count),
        label: `${count} bins`
    }));

    const handleHistogramRangeSelect = (range: HistogramRange) => {
        const groupId = activeGroup?.id ?? activeSource.id;
        getProps().onHistogramRangeSelect?.(groupId, range);
    };

    const handleCategoricalBarClick = (item: CategoryCount) => {
        const bucket = activeCategorical?.buckets.find((candidate) => candidate.id === item.id);
        if (!bucket || bucket.kind === 'other' || !activeGroup) return;
        getProps().onCategoricalValueToggle?.(activeGroup.id, bucket.value);
    };

    const handleCategoricalFilterToggle = (value: CategoricalMetadataValue) => {
        if (!activeGroup) return;
        getProps().onCategoricalValueToggle?.(activeGroup.id, value);
    };

    const handleCategoricalFilterClear = () => {
        if (!activeGroup) return;
        getProps().onCategoricalValuesClear?.(activeGroup.id);
    };

    const setCategoricalConfig = (next: DistributionConfig) => {
        if (!activeGroup) return;
        categoricalConfigs = {
            ...categoricalConfigs,
            [activeGroup.id]: { ...next, countMode: AnnotationCountMode.SAMPLES }
        };
    };

    function applyConfig(next: DistributionConfig) {
        if (activeCategorical) {
            setCategoricalConfig(next);
            return;
        }
        if (next.countMode !== config.countMode) {
            getProps().onCountModeChange?.(next.countMode ?? AnnotationCountMode.OBJECTS);
        }
        config = next;
    }

    return Object.assign(
        makeGetters({
            hasSourceSelector: () => hasSourceSelector,
            sourceItems: () => sourceItems,
            groupItems: () => groupItems,
            activeSource: () => activeSource,
            activeGroup: () => activeGroup,
            activeData: () => activeData,
            activeHistogram: () => activeHistogram,
            activeCategorical: () => activeCategorical,
            categoricalData: () => categoricalData,
            displayedData: () => displayedData,
            configurationItems: () => configurationItems,
            activeHistogramRange: () => activeHistogramRange,
            histogramTotal: () => histogramTotal,
            valueNoun: () => valueNoun,
            config: () => config,
            categoricalConfig: () => categoricalConfig,
            activeViewConfig: () => activeViewConfig,
            visible: () => visible,
            totalCount: () => totalCount,
            showTotalCount: () => showTotalCount
        }),
        {
            binCountItems,
            setSelectedSourceId: (id: string) => {
                selectedSourceId = id;
            },
            setSelectedGroupId: (id: string | undefined) => {
                selectedGroupId = id;
            },
            handleHistogramRangeSelect,
            handleCategoricalBarClick,
            handleCategoricalFilterToggle,
            handleCategoricalFilterClear,
            setCategoricalConfig,
            applyConfig
        }
    );
}
