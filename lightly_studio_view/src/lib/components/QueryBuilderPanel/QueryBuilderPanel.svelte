<script lang="ts">
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore — SVAR package has broken type paths; runtime works fine
    import { FilterBuilder, WillowDark } from '@svar-ui/svelte-filter';
    import type { IFilterSet, IField } from '$lib/types/svar-filter';
    import type { TagView as Tag } from '$lib/services/types';

    interface Props {
        tags: Tag[];
        onFilterChange: (filterSet: IFilterSet) => void;
    }

    const { tags, onFilterChange }: Props = $props();

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

    function handleChange(ev: { value: IFilterSet }) {
        onFilterChange(ev.value);
    }
</script>

<div class="query-builder-panel">
    <WillowDark fonts={false}>
        <FilterBuilder {fields} {options} onchange={handleChange} />
    </WillowDark>
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
</style>
