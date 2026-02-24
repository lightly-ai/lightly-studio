<script lang="ts">
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Brush, Eraser } from '@lucide/svelte';

    const { context: sampleDetailsToolbarContext, setBrushMode } = useSampleDetailsToolbarContext();

    const {
        context: annotationLabelContext,
        setAnnotationId,
        setLastCreatedAnnotationId
    } = useAnnotationLabelContext();
</script>

<div class="absolute bottom-11 w-full">
    <div
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
