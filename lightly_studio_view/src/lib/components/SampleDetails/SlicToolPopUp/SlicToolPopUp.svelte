<script lang="ts">
    import {
        useSampleDetailsToolbarContext,
        type SlicLevel
    } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { Button } from '$lib/components/ui/button';
    import FinishAnnotationButton from '../FinishAnnotationButton/FinishAnnotationButton.svelte';

    const { isPending = false }: { isPending?: boolean } = $props();
    const { context: sampleDetailsToolbarContext, setSlicLevel } = useSampleDetailsToolbarContext();

    const levelLabels: Record<SlicLevel, string> = {
        coarse: 'Coarse',
        medium: 'Medium',
        fine: 'Fine'
    };

    const orderedLevels: SlicLevel[] = ['coarse', 'medium', 'fine'];
</script>

<div class="absolute bottom-11 flex w-full justify-center">
    <div
        data-testid="slic-tool-popup"
        class="pointer-events-auto flex w-[240px] max-w-full select-none flex-col items-stretch gap-2 rounded-lg bg-muted p-2 shadow-md"
    >
        <div class="text-left">
            <h3 class="text-sm font-semibold text-foreground">AI-Assisted labeling</h3>
            <p class="text-xs text-muted-foreground">Click a superpixel to toggle it.</p>
        </div>

        <div class="flex flex-col gap-1">
            <span class="text-sm text-muted-foreground">Superpixel size</span>
            <div class="flex gap-1">
                {#each orderedLevels as level}
                    <Button
                        aria-pressed={sampleDetailsToolbarContext.slic.level === level}
                        variant={sampleDetailsToolbarContext.slic.level === level
                            ? 'default'
                            : 'outline'}
                        size="xs"
                        onclick={() => setSlicLevel(level)}
                    >
                        {levelLabels[level]}
                    </Button>
                {/each}
            </div>
        </div>

        <FinishAnnotationButton {isPending} />
    </div>
</div>
