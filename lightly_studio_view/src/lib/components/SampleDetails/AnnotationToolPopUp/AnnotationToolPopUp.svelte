<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Box, SquareDashed } from '@lucide/svelte';
    import AnnotationSourcePill from '$lib/components/AnnotationSourcePill/AnnotationSourcePill.svelte';
    import AnnotationClassSelect from '../AnnotationClassSelect/AnnotationClassSelect.svelte';

    interface Props {
        title: string;
        collectionId: string;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        outputType: 'mask' | 'box';
        onOutputTypeChange: (outputType: 'mask' | 'box') => void;
        canSave: boolean;
        onSave: () => void;
        onClear: () => void;
        children: Snippet;
    }

    let {
        title,
        collectionId,
        annotationClass,
        onAnnotationClassChange,
        outputType,
        onOutputTypeChange,
        canSave,
        onSave,
        onClear,
        children
    }: Props = $props();
</script>

<div class="absolute bottom-11 w-[min(90vw,265px)]">
    <div
        class="pointer-events-auto grid max-h-[70vh] gap-1.5 overflow-y-auto rounded-lg bg-muted p-2 shadow-md"
        role="dialog"
        aria-label={title}
    >
        <div class="truncate text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {title}
        </div>

        {@render children()}

        <div class="h-px bg-border"></div>

        <div class="min-w-0"><AnnotationSourcePill {collectionId} compact /></div>
        <AnnotationClassSelect
            {collectionId}
            value={annotationClass}
            onChange={onAnnotationClassChange}
            label="Annotation class"
            className="h-8"
        />

        <div class="flex overflow-hidden rounded-md border border-border">
            <button
                type="button"
                class={`flex h-8 flex-1 items-center justify-center gap-1 text-sm ${outputType === 'mask' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-muted'}`}
                aria-label="Mask output"
                aria-pressed={outputType === 'mask'}
                onclick={() => onOutputTypeChange('mask')}
            >
                <SquareDashed class="size-4" /> Mask
            </button>
            <button
                type="button"
                class={`flex h-8 flex-1 items-center justify-center gap-1 text-sm ${outputType === 'box' ? 'bg-primary/20 text-primary' : 'text-muted-foreground hover:bg-muted'}`}
                aria-label="Box output"
                aria-pressed={outputType === 'box'}
                onclick={() => onOutputTypeChange('box')}
            >
                <Box class="size-4" /> Box
            </button>
        </div>

        <div class="flex gap-1.5">
            <button
                type="button"
                class="h-8 flex-1 rounded-md bg-primary text-sm text-primary-foreground transition hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-50"
                aria-label="Save"
                disabled={!canSave}
                onclick={onSave}>Save</button
            >
            <button
                type="button"
                class="h-8 flex-1 rounded-md border border-border text-sm text-muted-foreground transition hover:bg-muted-foreground/10"
                aria-label="Clear"
                onclick={onClear}>Clear</button
            >
        </div>
    </div>
</div>
