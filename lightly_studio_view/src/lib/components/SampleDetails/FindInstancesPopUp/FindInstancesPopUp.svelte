<script lang="ts">
    import { Loader2, Sparkles, SquareDashedMousePointer } from '@lucide/svelte';
    import { Input } from '$lib/components/ui/input';
    import { cn } from '$lib/utils';
    import AnnotationToolPopUp from '$lib/components/SampleDetails/AnnotationToolPopUp/AnnotationToolPopUp.svelte';
    import type { SaveAs } from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
    import { canGenerateInstances } from '$lib/components/SampleDetails/FindInstancesOverlay/FindInstancesOverlay.helpers';
    import MaxInstancesInput from './MaxInstancesInput/MaxInstancesInput.svelte';

    interface Props {
        collectionId: string;
        prompt: string;
        onPromptChange: (prompt: string) => void;
        maxInstances: number;
        onMaxInstancesChange: (value: number) => void;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
        isDrawingBox: boolean;
        onDrawBoxChange: (isDrawingBox: boolean) => void;
        boxCount: number;
        isGenerating: boolean;
        resultCount: number;
        canSave: boolean;
        onGenerate: () => void;
        onSave: () => void;
        onClear: () => void;
    }

    let {
        collectionId,
        prompt,
        onPromptChange,
        maxInstances,
        onMaxInstancesChange,
        annotationClass,
        onAnnotationClassChange,
        saveAs,
        onSaveAsChange,
        isDrawingBox,
        onDrawBoxChange,
        boxCount,
        isGenerating,
        resultCount,
        canSave,
        onGenerate,
        onSave,
        onClear
    }: Props = $props();

    const canGenerate = $derived(canGenerateInstances({ prompt }) && !isGenerating);

    const iconButtonClass =
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border transition disabled:pointer-events-none disabled:opacity-50';
</script>

<AnnotationToolPopUp
    title="Find all instances"
    {collectionId}
    {annotationClass}
    {onAnnotationClassChange}
    {saveAs}
    {onSaveAsChange}
    {canSave}
    {onSave}
    {onClear}
>
    <p class="text-xs text-muted-foreground">Type a prompt. Draw boxes to show more examples.</p>
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
    <MaxInstancesInput value={maxInstances} onChange={onMaxInstancesChange} />
</AnnotationToolPopUp>
