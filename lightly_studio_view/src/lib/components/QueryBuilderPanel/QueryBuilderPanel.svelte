<script lang="ts">
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore — SVAR package has broken type paths; runtime works fine
    import { FilterBuilder, FilterQuery, WillowDark } from '@svar-ui/svelte-filter';
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore — SVAR package has broken type paths; runtime works fine
    import { serialize } from '@svar-ui/filter-store';
    import type { IFilterSet, IField, FilterQueryEvent } from '$lib/types/svar-filter';
    import type { TagView as Tag } from '$lib/services/types';
    import type { components } from '$lib/schema';
    type QueryFieldSchema = components['schemas']['QueryFieldSchema'];
    type QueryFieldsResponse = components['schemas']['QueryFieldsResponse'];
    import { LayoutList, Braces, Terminal } from '@lucide/svelte';
    import { onMount } from 'svelte';
    import QueryCodeEditor from '$lib/components/QueryCodeEditor/QueryCodeEditor.svelte';

    interface Props {
        tags: Tag[];
        type?: 'list' | 'line' | 'simple';
        onFilterChange: (filterSet: IFilterSet, schemas: QueryFieldSchema[]) => void;
        onPythonQueryRun?: (query: string) => void;
    }

    const { tags, type = 'list', onFilterChange, onPythonQueryRun }: Props = $props();

    let fieldSchemas = $state<QueryFieldSchema[]>([]);

    onMount(async () => {
        const res = await fetch('/api/query_fields');
        if (res.ok) {
            const data = (await res.json()) as QueryFieldsResponse;
            fieldSchemas = data.fields;
        }
    });

    const fields = $derived<IField[]>(
        fieldSchemas.map((f) => ({ id: f.id, label: f.label, type: f.type }))
    );

    const options = $derived({
        tag: tags.map((t) => t.name)
    });

    let viewMode = $state<'builder' | 'dsl' | 'python'>('builder');
    let currentFilterSet = $state<IFilterSet>({});
    let dslText = $state('');

    function handleBuilderChange(ev: { value: IFilterSet }) {
        currentFilterSet = ev.value;
        onFilterChange(ev.value, fieldSchemas);
    }

    function switchToDsl() {
        dslText = (serialize(currentFilterSet) as { query: string }).query;
        viewMode = 'dsl';
    }

    function switchToBuilder() {
        viewMode = 'builder';
    }

    function switchToPython() {
        viewMode = 'python';
    }

    async function handleDslChange(ev: FilterQueryEvent) {
        // naturalText is set for mixed input (DSL + free text).
        // For pure free text, SVAR sets ev.error and puts the raw text in ev.text.
        // Both cases should trigger AI translation.
        const naturalInput = ev.parsed?.naturalText || (ev.error && ev.text ? ev.text : null);

        if (naturalInput) {
            ev.startProgress();
            try {
                const res = await fetch('/api/translate_query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: naturalInput })
                });
                if (res.ok) {
                    const { query } = (await res.json()) as { query: string };
                    // Updating dslText causes FilterQuery to re-parse and fire onchange
                    // again with the valid DSL — that second call updates currentFilterSet.
                    if (query) dslText = query;
                } else {
                    const { detail } = (await res.json()) as { detail: string };
                    console.error('translate_query failed:', detail);
                }
            } finally {
                ev.endProgress();
            }
            return;
        }

        // Valid DSL: update the shared filter set
        if (!ev.error && ev.parsed?.config) {
            const parsed = ev.parsed.config as IFilterSet;
            currentFilterSet = parsed;
            onFilterChange(parsed, fieldSchemas);
        }
    }
</script>

<div
    class="query-builder-panel flex min-w-0 {viewMode === 'python'
        ? 'flex-col gap-2'
        : 'items-center gap-2'}"
>
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
        <button
            class="flex h-8 w-8 items-center justify-center transition-colors {viewMode === 'python'
                ? 'bg-secondary text-secondary-foreground'
                : 'text-muted-foreground hover:bg-accent'}"
            onclick={switchToPython}
            title="Python editor"
        >
            <Terminal class="h-4 w-4" />
        </button>
    </div>

    {#if viewMode === 'python'}
        <QueryCodeEditor onrun={(q) => onPythonQueryRun?.(q)} />
    {:else}
        <div class="min-w-0 flex-1">
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
                        parse="allowFreeText"
                        onchange={handleDslChange}
                    />
                {/if}
            </WillowDark>
        </div>
    {/if}
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

    /* Fill the container width so the toolbar has a fixed reference width */
    :global(.query-builder-panel .wx-willow-dark-theme),
    :global(.query-builder-panel .wx-filter-builder.wx-line),
    :global(.query-builder-panel .wx-toolbar.wx-line) {
        width: 100%;
    }

    /* Override SVAR's hardcoded 67px toolbar height in line mode */
    :global(.query-builder-panel .wx-toolbar.wx-line) {
        height: 40px !important;
        gap: 8px;
    }

    /* Give .wx-filters a constrained width so overflow-x:auto (already set by SVAR) kicks in.
       overflow-y:hidden prevents the horizontal scrollbar from triggering overflow-y:auto,
       which would eat into the 40px toolbar height and clip the filter chips.
       The scrollbar is hidden visually; users scroll horizontally via touch-pad or shift+wheel. */
    :global(.query-builder-panel .wx-toolbar.wx-line .wx-filters) {
        flex: 1;
        min-width: 0;
        overflow-y: hidden;
        scrollbar-width: none;
    }
    :global(.query-builder-panel .wx-toolbar.wx-line .wx-filters::-webkit-scrollbar) {
        display: none;
    }

    /* Force the group to be at least as wide as all its chips laid out in one row.
       min-width:max-content prevents flex-shrink from compressing the group to fit
       inside .wx-filters — without this the group shrinks instead of overflowing,
       so the overflow-x:auto scroll on .wx-filters never triggers. */
    :global(.query-builder-panel .wx-group.wx-line) {
        flex-wrap: nowrap;
        min-width: max-content;
    }
</style>
