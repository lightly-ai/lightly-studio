<script lang="ts">
    import { ZoomIn, ZoomOut } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { Snippet } from 'svelte';

    const {
        onZoomReset,
        onZoomIn,
        onZoomOut,
        scale,
        isZoominDisabled,
        isZoomoutDisabled,
        isResetDisabled,
        content,
        contentRight
    }: {
        onZoomIn: () => void;
        onZoomOut: () => void;
        scale: number;
        onZoomReset: () => void;
        isZoominDisabled?: boolean;
        isZoomoutDisabled?: boolean;
        isResetDisabled?: boolean;
        content?: Snippet;
        contentRight?: Snippet;
    } = $props();
</script>

<div class="pointer-events-none absolute bottom-0 left-1 z-20 w-[200px]">
    {#if content}
        {@render content()}
    {/if}
    <div
        class="
      pointer-events-auto
      flex
      w-full
      items-center
      gap-1
      rounded-lg
      bg-muted/80
      shadow-md
      backdrop-blur-sm
    "
    >
        <Button
            variant="ghost"
            buttonProps={{
                size: 'sm',
                onclick: onZoomReset,
                disabled: isResetDisabled,
                'data-testid': 'zoom-reset-button'
            }}
        >
            Reset
        </Button>

        <div class="h-6 w-px bg-white/20"></div>

        <Button
            variant="ghost"
            ariaLabel="zoom out"
            icon={ZoomOut}
            buttonProps={{
                title: 'zoom out',
                size: 'icon',
                onclick: onZoomOut,
                disabled: isZoominDisabled,
                'data-testid': 'zoom-out-button'
            }}
        />

        <div class="w-[32px] text-center text-sm text-muted-foreground" data-testid="zoom-scale">
            {Math.round(scale * 100)}%
        </div>

        <Button
            variant="ghost"
            ariaLabel="zoom in"
            icon={ZoomIn}
            buttonProps={{
                title: 'zoom in',
                size: 'icon',
                onclick: onZoomIn,
                disabled: isZoomoutDisabled,
                'data-testid': 'zoom-in-button'
            }}
        />
    </div>
    {#if contentRight}
        <div class="pointer-events-none absolute bottom-0 left-[calc(100%+0.5rem)]">
            <div class="pointer-events-auto">
                {@render contentRight()}
            </div>
        </div>
    {/if}
</div>
