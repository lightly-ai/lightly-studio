<script lang="ts">
    import type { Snippet } from 'svelte';
    import GridItemTag from './GridItemTag.svelte';
    import { DRAG_PREVIEW_OFFSET_PX, type GridItemDragData } from './GridItem.constants';
    import { useGridItemDrag } from '$lib/hooks/useGridItemDrag/useGridItemDrag.svelte';

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
        dragData,
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
        dragData?: GridItemDragData;
        onSelect?: (event: MouseEvent | KeyboardEvent) => void;
        ondblclick?: (event: MouseEvent) => void;
    } = $props();

    const drag = useGridItemDrag(() => dragData);

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }

    function handleOnClick(event: MouseEvent) {
        if (!onSelect) return;
        if (drag.suppressNextClick) {
            drag.suppressNextClick = false;
            event.preventDefault();
            return;
        }
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
        draggable="false"
        class:cursor-grab={dragData && !drag.isPointerDragging}
        class:cursor-grabbing={drag.isPointerDragging}
        {ondblclick}
        onclick={handleOnClick}
        onpointerdown={drag.handlePointerDown}
        onpointermove={drag.handlePointerMove}
        onpointerup={drag.handlePointerUp}
        onpointercancel={drag.handlePointerCancel}
        onlostpointercapture={drag.handleLostPointerCapture}
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

{#if dragData && drag.dragPreview}
    <div
        class="pointer-events-none fixed z-50 h-20 w-20 overflow-hidden rounded-md border border-primary/60 bg-background opacity-80 shadow-xl ring-2 ring-primary/30"
        style="left: {drag.dragPreview.x + DRAG_PREVIEW_OFFSET_PX}px; top: {drag.dragPreview.y +
            DRAG_PREVIEW_OFFSET_PX}px;"
        data-testid="grid-item-drag-preview"
    >
        <img src={dragData.url} alt="" class="h-full w-full object-cover" draggable="false" />
    </div>
{/if}
