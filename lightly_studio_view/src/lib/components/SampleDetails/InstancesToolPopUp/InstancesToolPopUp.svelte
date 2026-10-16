<script lang="ts">
    import { Loader2, Sparkles, SquareDashedMousePointer } from '@lucide/svelte';
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils';
    import AnnotationToolPopUp from '../AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { OutputType } from '../AnnotationPreview/annotationPreview.helpers';
    import { canGenerateInstances } from '../InstancesOverlay/InstancesOverlay.helpers';

    interface Props {
        collectionId: string;
        prompt: string;
        onPromptChange: (prompt: string) => void;
        maxInstances: number;
        maxInstancesLimit: number;
        onMaxInstancesChange: (value: number) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        outputType: OutputType;
        onOutputTypeChange: (outputType: OutputType) => void;
        canDrawBoxes: boolean;
        isDrawingBox: boolean;
        onDrawBoxChange: (isDrawingBox: boolean) => void;
        boxCount: number;
        isGenerating: boolean;
        resultCount: number;
        onGenerate: () => void;
        onSave: () => void;
        onClear: () => void;
    }

    let {
        collectionId,
        prompt,
        onPromptChange,
        maxInstances,
        maxInstancesLimit,
        onMaxInstancesChange,
        annotationClass,
        onAnnotationClassChange,
        outputType,
        onOutputTypeChange,
        canDrawBoxes,
        isDrawingBox,
        onDrawBoxChange,
        boxCount,
        isGenerating,
        resultCount,
        onGenerate,
        onSave,
        onClear
    }: Props = $props();

    const canGenerate = $derived(canGenerateInstances({ prompt, boxCount }) && !isGenerating);

    const clampMaxInstances = (value: number) =>
        Math.min(maxInstancesLimit, Math.max(1, Math.round(value) || 1));

    const iconButtonClass =
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border transition disabled:pointer-events-none disabled:opacity-50';
</script>

<AnnotationToolPopUp
    title="Find all instances"
    {collectionId}
    {annotationClass}
    {onAnnotationClassChange}
    {outputType}
    {onOutputTypeChange}
    canSave={resultCount > 0}
    {onSave}
    {onClear}
>
    <p class="text-xs text-muted-foreground">
        {canDrawBoxes ? 'Type a prompt, draw boxes, or both.' : 'Type a prompt.'}
    </p>
    <div class="flex items-center gap-1.5">
        <Input
            class="h-8"
            wrapperClass="min-w-0 flex-1"
            aria-label="Instance prompt"
            placeholder="e.g. cars"
            value={prompt}
            oninput={(event) => onPromptChange(event.currentTarget.value)}
            onkeydown={(event) => event.key === 'Enter' && canGenerate && onGenerate()}
        />
        {#if canDrawBoxes}
            <button
                type="button"
                class={cn(
                    iconButtonClass,
                    isDrawingBox
                        ? 'bg-primary/20 text-primary'
                        : 'text-muted-foreground hover:bg-muted-foreground/10'
                )}
                aria-label={isDrawingBox ? 'Stop drawing boxes' : 'Draw box'}
                aria-pressed={isDrawingBox}
                title={boxCount > 0 ? `Draw box (${boxCount} drawn)` : 'Draw box'}
                onclick={() => onDrawBoxChange(!isDrawingBox)}
            >
                <SquareDashedMousePointer class="size-4" />
            </button>
        {/if}
        <button
            type="button"
            class={cn(
                iconButtonClass,
                'border-transparent bg-primary text-primary-foreground hover:bg-primary/90'
            )}
            aria-label="Find instances"
            title={resultCount > 0 ? `Find instances (${resultCount} found)` : 'Find instances'}
            disabled={!canGenerate}
            onclick={onGenerate}
        >
            {#if isGenerating}
                <Loader2 class="size-4 animate-spin" />
            {:else}
                <Sparkles class="size-4" />
            {/if}
        </button>
    </div>
    <label class="flex items-center justify-between gap-2 text-xs text-muted-foreground">
        Maximum instances
        <Input
            type="number"
            class="h-8 w-16"
            wrapperClass="w-auto"
            min={1}
            max={maxInstancesLimit}
            value={maxInstances}
            onchange={(event) => {
                const value = clampMaxInstances(event.currentTarget.valueAsNumber);
                event.currentTarget.value = String(value);
                onMaxInstancesChange(value);
            }}
        />
    </label>
</AnnotationToolPopUp>
