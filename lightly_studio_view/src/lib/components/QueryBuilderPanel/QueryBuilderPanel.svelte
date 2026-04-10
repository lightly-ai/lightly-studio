<script lang="ts">
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore — SVAR package has broken type paths; runtime works fine
    import { FilterBuilder, FilterQuery, WillowDark } from '@svar-ui/svelte-filter';
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore — SVAR package has broken type paths; runtime works fine
    import { serialize } from '@svar-ui/filter-store';
    import type { IFilterSet, IField, FilterQueryEvent } from '$lib/types/svar-filter';
    import type { TagView as Tag } from '$lib/services/types';
    import { LayoutList, Braces } from '@lucide/svelte';

    interface Props {
        tags: Tag[];
        type?: 'list' | 'line' | 'simple';
        onFilterChange: (filterSet: IFilterSet) => void;
    }

    const { tags, type = 'list', onFilterChange }: Props = $props();

    const fields: IField[] = [
        { id: 'tag', label: 'Tag', type: 'text' },
        { id: 'file_name', label: 'File Name', type: 'text' },
        { id: 'created_at', label: 'Created At', type: 'date' },
        { id: 'width', label: 'Width (px)', type: 'number' },
        { id: 'height', label: 'Height (px)', type: 'number' }
    ];

    const options = $derived({
        tag: tags.map((t) => t.name)
    });

    let viewMode = $state<'builder' | 'dsl'>('builder');
    let currentFilterSet = $state<IFilterSet>({});
    let dslText = $state('');

    function handleBuilderChange(ev: { value: IFilterSet }) {
        currentFilterSet = ev.value;
        onFilterChange(ev.value);
    }

    function switchToDsl() {
        dslText = (serialize(currentFilterSet) as { query: string }).query;
        viewMode = 'dsl';
    }

    function switchToBuilder() {
        viewMode = 'builder';
    }

    function handleDslChange(ev: FilterQueryEvent) {
        if (ev.error || !ev.parsed?.config) return;
        const parsed = ev.parsed.config as IFilterSet;
        currentFilterSet = parsed;
        onFilterChange(parsed);
    }
</script>

<div class="query-builder-panel flex min-w-0 items-center gap-2">
    <div class="flex shrink-0 overflow-hidden rounded-md border border-input">
        <button
            class="flex h-8 w-8 items-center justify-center transition-colors {viewMode === 'builder'
                ? 'bg-secondary text-secondary-foreground'
                : 'text-muted-foreground hover:bg-accent'}"
            onclick={switchToBuilder}
            title="Visual builder"
        >
            <LayoutList class="h-4 w-4" />
        </button>
        <button
            class="flex h-8 w-8 items-center justify-center transition-colors {viewMode === 'dsl'
                ? 'bg-secondary text-secondary-foreground'
                : 'text-muted-foreground hover:bg-accent'}"
            onclick={switchToDsl}
            title="DSL editor"
        >
            <Braces class="h-4 w-4" />
        </button>
    </div>

    <div class="min-w-0 flex-1 overflow-hidden">
        <WillowDark fonts={false}>
            {#if viewMode === 'builder'}
                <FilterBuilder
                    {type}
                    {fields}
                    {options}
                    value={currentFilterSet}
                    onchange={handleBuilderChange}
                />
            {:else}
                <FilterQuery
                    value={dslText}
                    {fields}
                    {options}
                    parse="strict"
                    onchange={handleDslChange}
                />
            {/if}
        </WillowDark>
    </div>
</div>

<style>
    /* Map SVAR WillowDark variables to the app's Tailwind CSS theme tokens. */
    :global(.query-builder-panel .wx-willow-dark-theme) {
        --wx-background: hsl(var(--card));
        --wx-background-alt: hsl(var(--muted));
        --wx-background-hover: hsl(var(--accent));
        --wx-color-font: hsl(var(--foreground));
        --wx-color-font-alt: hsl(var(--muted-foreground));
        --wx-color-primary: hsl(var(--primary));
        --wx-color-primary-selected: hsl(var(--primary) / 0.2);
        --wx-color-primary-font: hsl(var(--primary-foreground));
        --wx-color-secondary-hover: hsl(var(--primary) / 0.12);
        --wx-color-secondary-font: hsl(var(--primary));
        --wx-icon-color: hsl(var(--muted-foreground));
        --wx-border: 1px solid hsl(var(--border));
        --wx-border-light: 1px solid hsl(var(--border));
        --wx-border-medium: 1px solid hsl(var(--border));
        --wx-border-radius: calc(var(--radius) - 2px);
        --wx-filter-border: 1px solid hsl(var(--border));
        --wx-filter-value-color: hsl(var(--primary));
        --wx-popup-background: hsl(var(--card));
        --wx-popup-border: 1px solid hsl(var(--border));
    }

    :global(.query-builder-panel .wx-willow-dark-theme) {
        height: auto !important;
        max-width: 100%;
    }
</style>
