<script lang="ts">
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useSettings } from '$lib/hooks/useSettings';
    import { isInputElement } from '$lib/utils/isInputElement';
    import { Brush, Eraser } from '@lucide/svelte';
    import { onDestroy, onMount } from 'svelte';

    const {
        context: sampleDetailsToolbarContext,
        setBrushMode,
        setBrushSize
    } = useSampleDetailsToolbarContext();
    const { settingsStore } = useSettings();

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setLastCreatedAnnotationId,
        setIsChangingBrushSize
    } = useAnnotationLabelContext();

    const normalizeShortcut = (key: string): string => (key.length === 1 ? key.toLowerCase() : key);

    const MIN_BRUSH_SIZE = 1;
    const MAX_BRUSH_SIZE = 100;
    const WHEEL_STEP = 1;

    const clampBrushSize = (size: number): number =>
        Math.min(MAX_BRUSH_SIZE, Math.max(MIN_BRUSH_SIZE, size));

    const onKeyDown = (event: KeyboardEvent) => {
        const target = event.target as HTMLElement;
        if (target?.isContentEditable || isInputElement(target)) return;

        const key = normalizeShortcut(event.key);
        const brushShortcut = normalizeShortcut($settingsStore.key_toolbar_brush || 'r');
        const eraserShortcut = normalizeShortcut($settingsStore.key_toolbar_eraser || 'x');

        if (key === brushShortcut) {
            event.preventDefault();
            setBrushMode('brush');
        } else if (key === eraserShortcut) {
            event.preventDefault();
            setBrushMode('eraser');
        }
    };

    const onWheel = (event: WheelEvent) => {
        const target = event.target as HTMLElement;

        if (target?.isContentEditable || isInputElement(target)) return;
        if (!event.altKey) return;
        setIsChangingBrushSize(true);

        const direction = event.deltaY < 0 ? 1 : -1;
        const nextSize = clampBrushSize(
            sampleDetailsToolbarContext.brush.size + direction * WHEEL_STEP
        );

        if (nextSize !== sampleDetailsToolbarContext.brush.size) {
            event.preventDefault();
            setBrushSize(nextSize);
        }

        // Prevent enabling zoom immediately
        setTimeout(() => setIsChangingBrushSize(false), 100);
    };

    onMount(() => {
        window.addEventListener('keydown', onKeyDown);
        // Use capture so wheel updates still work if inner components stop propagation.
        window.addEventListener('wheel', onWheel, { passive: false, capture: true });
    });

    onDestroy(() => {
        window.removeEventListener('keydown', onKeyDown);
        window.removeEventListener('wheel', onWheel, { capture: true });
    });
</script>

<div class="absolute bottom-11 w-full">
    <div
        data-testid="brush-tool-popup"
        class="
      pointer-events-auto
      flex
      w-full
      select-none
      flex-col
      items-stretch
      gap-1
      rounded-lg
      bg-muted
      shadow-md
    "
    >
        <div class="px-2 py-2 text-left">
            <h3 class="text-sm font-semibold text-foreground">Brush Tool</h3>
        </div>

        <div class="px-2">
            <div class="gap- flex items-center">
                <span class="w-16 text-sm text-muted-foreground"> Mode: </span>

                <div class="flex overflow-hidden rounded-lg border border-border">
                    <button
                        aria-label="Brush mode"
                        title={`Shortcut: ${($settingsStore.key_toolbar_brush || 'r').toUpperCase()}`}
                        class="
              flex h-9 w-12 items-center justify-center transition
              {sampleDetailsToolbarContext.brush.mode === 'brush'
                            ? 'bg-primary/20 text-primary'
                            : 'text-muted-foreground hover:bg-muted'}
            "
                        onclick={() => setBrushMode('brush')}
                    >
                        <Brush class="h-4 w-4" />
                    </button>

                    <button
                        aria-label="Eraser mode"
                        title={`Shortcut: ${($settingsStore.key_toolbar_eraser || 'x').toUpperCase()}`}
                        class="
              flex h-9 w-12 items-center justify-center transition
              {sampleDetailsToolbarContext.brush.mode === 'eraser'
                            ? 'bg-primary/20 text-primary'
                            : 'text-muted-foreground hover:bg-muted'}
            "
                        onclick={() => setBrushMode('eraser')}
                    >
                        <Eraser class="h-4 w-4" />
                    </button>
                </div>
            </div>

            <div class="flex items-center gap-4 pb-2 pt-2">
                <span class="w-16 text-sm text-muted-foreground"> Size: </span>

                <input
                    type="range"
                    min="1"
                    max="100"
                    bind:value={sampleDetailsToolbarContext.brush.size}
                    class="w-full accent-primary"
                />
            </div>
        </div>
        {#if !annotationLabelContext.isOnAnnotationDetailsView}
            <div class="px-2 pb-2">
                <button
                    class="w-full translate-y-1 rounded bg-primary p-1 text-center text-accent-foreground
         transition-all duration-300 ease-out
         animate-in fade-in hover:bg-primary/90"
                    type="button"
                    aria-label="Finish"
                    onclick={() => {
                        setAnnotationId(null);
                        setLastCreatedAnnotationId(null);
                    }}><span class="text-sm text-primary-foreground">Finish</span></button
                >
            </div>
        {/if}
    </div>
</div>
