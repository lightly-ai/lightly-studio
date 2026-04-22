<script lang="ts">
    import type { Snippet } from 'svelte';
    import GridItemTag from './GridItemTag.svelte';

    let {
        children,
        width = 300,
        height = 300,
        style,
        dataTestId,
        ariaLabel = 'View item',
        isSelected = false,
        tag = true,
        caption,
        dataSampleName,
        dataIndex,
        onSelect,
        ondblclick
    }: {
        children: Snippet;
        width?: string | number;
        height?: string | number;
        style?: string;
        dataTestId?: string;
        ariaLabel?: string;
        isSelected?: boolean;
        tag?: boolean;
        caption?: string;
        dataSampleName?: string;
        dataIndex?: number;
        onSelect?: (event: MouseEvent | KeyboardEvent) => void;
        ondblclick?: (event: MouseEvent) => void;
    } = $props();

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }

    function handleOnClick(event: MouseEvent) {
        if (!onSelect) return;
        event.preventDefault();
        onSelect(event);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (!onSelect) return;
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        onSelect(event);
    }
</script>

<div class="select-none" {style}>
    <div
        class="relative overflow-hidden rounded-lg dark:[color-scheme:dark]"
        class:grid-item-selected={isSelected}
        style="width: {formatSize(width)}; height: {formatSize(height)};"
        data-testid={dataTestId}
        data-sample-name={dataSampleName}
        data-index={dataIndex}
        {ondblclick}
        onclick={handleOnClick}
        onkeydown={handleKeyDown}
        aria-label={ariaLabel}
        role="button"
        tabindex="0"
    >
        {#if tag}
            <GridItemTag {isSelected} />
        {/if}

        {@render children()}

        {#if caption}
            <div
                class="pointer-events-none absolute inset-x-0 bottom-0 z-10 rounded-b-lg bg-black/60 px-2 py-1 text-xs font-medium text-white"
                data-testid="grid-item-caption"
            >
                <span class="block truncate" title={caption} data-testid="grid-item-caption-text">
                    {caption}
                </span>
            </div>
        {/if}
    </div>
</div>
