<script lang="ts">
    import { Select, type SelectItem } from '$lib/components/Select';
    import * as Tabs from '$lib/components/ui/tabs';
    import {
        CLASS_LIMIT_OPTIONS,
        PER_CLASS_VIEWS,
        PER_CLASS_VIEW_LABELS,
        type ClassLimit,
        type PerClassView
    } from '../../EvaluationComparison.helpers';

    interface Props {
        view: PerClassView;
        onViewChange: (view: PerClassView) => void;
        classLimit: ClassLimit;
        onClassLimitChange: (classLimit: ClassLimit) => void;
        shownClassCount: number;
        totalClassCount: number;
    }

    const {
        view,
        onViewChange,
        classLimit,
        onClassLimitChange,
        shownClassCount,
        totalClassCount
    }: Props = $props();

    const ALL_CLASSES_KEY = 'all';

    const classLimitKey = (limit: ClassLimit): string =>
        limit === null ? ALL_CLASSES_KEY : String(limit);

    const classLimitItems: SelectItem[] = CLASS_LIMIT_OPTIONS.map((limit) => ({
        value: classLimitKey(limit),
        label: limit === null ? 'All classes' : `Top ${limit}`
    }));

    // The "All classes" option is null, so search by index: `find` cannot tell it from no match.
    const selectClassLimit = (key: string) => {
        const index = CLASS_LIMIT_OPTIONS.findIndex((limit) => classLimitKey(limit) === key);
        if (index >= 0) onClassLimitChange(CLASS_LIMIT_OPTIONS[index]);
    };

    const selectView = (value: string) => {
        const selectedView = PER_CLASS_VIEWS.find((candidate) => candidate === value);
        if (selectedView) onViewChange(selectedView);
    };

    const isLimited = $derived(shownClassCount < totalClassCount);
</script>

<div class="flex flex-wrap items-center justify-between gap-2">
    <span class="text-xs text-muted-foreground" data-testid="per-class-shown-count">
        {#if isLimited}
            {shownClassCount} of {totalClassCount} annotation classes with the largest gap between runs
        {:else}
            {totalClassCount} annotation classes, largest gap between runs first
        {/if}
    </span>
    <div class="flex items-center gap-2">
        <Select
            items={classLimitItems}
            value={classLimitKey(classLimit)}
            size="xs"
            class="w-32"
            testId="per-class-limit"
            selectProps={{ 'aria-label': 'Number of annotation classes' }}
            onValueChange={selectClassLimit}
        />
        <Tabs.Root value={view} onValueChange={selectView}>
            <Tabs.List>
                {#each PER_CLASS_VIEWS as viewOption (viewOption)}
                    <Tabs.Trigger value={viewOption}
                        >{PER_CLASS_VIEW_LABELS[viewOption]}</Tabs.Trigger
                    >
                {/each}
            </Tabs.List>
        </Tabs.Root>
    </div>
</div>
