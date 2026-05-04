<script lang="ts">
    import type { Snippet } from 'svelte';
    import GridItemTag from './GridItemTag.svelte';

    export type GridItemDragData = {
        url: string;
        fileName: string;
    };

    const GRID_ITEM_DRAG_MIME_TYPE = 'application/vnd.lightly-studio.grid-image+json';
    const DRAG_START_THRESHOLD_PX = 8;

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

    let suppressNextClick = false;
    let pointerStart: { x: number; y: number } | null = null;

    function formatSize(value: string | number): string {
        return typeof value === 'number' ? `${value}px` : value;
    }

    function handleOnClick(event: MouseEvent) {
        if (!onSelect) return;
        if (suppressNextClick) {
            suppressNextClick = false;
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

    function suppressNextSelectionClick() {
        suppressNextClick = true;
        window.setTimeout(() => {
            suppressNextClick = false;
        }, 100);
    }

    function handleDragStart(event: DragEvent) {
        if (!dragData || !event.dataTransfer) {
            event.preventDefault();
            return;
        }

        if (pointerStart && event.clientX != null && event.clientY != null) {
            const deltaX = event.clientX - pointerStart.x;
            const deltaY = event.clientY - pointerStart.y;
            const distance = Math.hypot(deltaX, deltaY);
            if (distance < DRAG_START_THRESHOLD_PX) {
                event.preventDefault();
                return;
            }
        }

        suppressNextSelectionClick();
        event.dataTransfer.effectAllowed = 'copy';
        event.dataTransfer.setData(GRID_ITEM_DRAG_MIME_TYPE, JSON.stringify(dragData));
        event.dataTransfer.setData('text/uri-list', dragData.url);
        event.dataTransfer.setData('text/plain', dragData.url);
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
        draggable={dragData ? 'true' : 'false'}
        {ondblclick}
        onclick={handleOnClick}
        onmousedown={(event) => {
            pointerStart = { x: event.clientX, y: event.clientY };
        }}
        ondragstart={handleDragStart}
        ondragend={() => {
            suppressNextSelectionClick();
            pointerStart = null;
        }}
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
