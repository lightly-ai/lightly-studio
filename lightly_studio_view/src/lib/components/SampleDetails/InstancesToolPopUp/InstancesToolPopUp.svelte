<script lang="ts">
    import { Loader2, Sparkles, SquareDashedMousePointer } from '@lucide/svelte';
    import { Input } from '$lib/components/ui/input';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import AnnotationToolPopUp from '../AnnotationToolPopUp/AnnotationToolPopUp.svelte';

    interface Props {
        collectionId: string;
        prompt: string;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        outputType: 'mask' | 'box';
        onOutputTypeChange: (outputType: 'mask' | 'box') => void;
        isDrawingBox: boolean;
        onDrawBox: () => void;
        onCancelDrawBox: () => void;
        onPromptChange: (prompt: string) => void;
        boxCount: number;
        canGenerate: boolean;
        isGenerating: boolean;
        resultCount: number;
        onGenerate: () => void;
        onSave: () => void;
        onClear: () => void;
    }

    let {
        collectionId,
        prompt,
        annotationClass,
        onAnnotationClassChange,
        outputType,
        onOutputTypeChange,
        isDrawingBox,
        onDrawBox,
        onCancelDrawBox,
        onPromptChange,
        boxCount,
        canGenerate,
        isGenerating,
        resultCount,
        onGenerate,
        onSave,
        onClear
    }: Props = $props();
    const { setLastAnnotationOutputType } = useGlobalStorage();
    const select = (value: 'mask' | 'box') => {
        onOutputTypeChange(value);
        setLastAnnotationOutputType(value);
    };

    const iconButtonClass =
        'flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border transition disabled:pointer-events-none disabled:opacity-50';
</script>

<AnnotationToolPopUp
    title="Find all instances"
    {collectionId}
    {annotationClass}
    {onAnnotationClassChange}
    {outputType}
    onOutputTypeChange={select}
    canSave={resultCount > 0}
    {onSave}
    {onClear}
>
    <p class="text-xs text-muted-foreground">Type a prompt, draw boxes, or both.</p>
    <div class="flex items-center gap-1.5">
        <Input
            class="h-8"
            wrapperClass="min-w-0 flex-1"
            aria-label="Instance prompt"
            placeholder="e.g. cars"
            value={prompt}
            oninput={(event) => onPromptChange(event.currentTarget.value)}
        />
        <button
            type="button"
            class={`${iconButtonClass} ${isDrawingBox ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-muted-foreground/10'}`}
            aria-label={isDrawingBox ? 'Stop drawing boxes' : 'Draw box'}
            aria-pressed={isDrawingBox}
            title={boxCount > 0 ? `Draw box (${boxCount} drawn)` : 'Draw box'}
            onclick={isDrawingBox ? onCancelDrawBox : onDrawBox}
        >
            <SquareDashedMousePointer class="size-4" />
        </button>
        <button
            type="button"
            class={`${iconButtonClass} border-transparent bg-primary text-primary-foreground hover:bg-primary/90`}
            aria-label="Generate instances"
            title={resultCount > 0 ? `Generate (${resultCount} found)` : 'Generate'}
            disabled={!canGenerate || isGenerating}
            onclick={onGenerate}
        >
            {#if isGenerating}
                <Loader2 class="size-4 animate-spin" />
            {:else}
                <Sparkles class="size-4" />
            {/if}
        </button>
    </div>
</AnnotationToolPopUp>
