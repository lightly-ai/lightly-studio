<script lang="ts">
    import type { Snippet } from 'svelte';
    import { Box, SquareDashed } from '@lucide/svelte';
    import { cn } from '$lib/utils';
    import { Button } from '$lib/components/ui/button';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';

    type SaveAs = (typeof saveAsOptions)[number]['value'];

    interface Props {
        title: string;
        collectionId: string;
        annotationClass?: string | null;
        onAnnotationClassChange: (value: string) => void;
        saveAs: SaveAs;
        onSaveAsChange: (saveAs: SaveAs) => void;
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
        saveAs,
        onSaveAsChange,
        canSave,
        onSave,
        onClear,
        children
    }: Props = $props();

    const saveAsOptions = [
        { value: 'mask', label: 'Mask', icon: SquareDashed },
        { value: 'box', label: 'Box', icon: Box }
    ] as const;
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

        <AnnotationClassSelect
            {collectionId}
            value={annotationClass}
            onChange={onAnnotationClassChange}
            label="Annotation class"
            className="h-8"
        />

        <div
            class="flex overflow-hidden rounded-md border border-border"
            role="group"
            aria-label="Save as"
        >
            {#each saveAsOptions as option (option.value)}
                <Button
                    variant="ghost"
                    class={cn(
                        'h-8 flex-1 gap-1 rounded-none',
                        saveAs === option.value
                            ? 'bg-primary/20 text-primary hover:bg-primary/20 hover:text-primary'
                            : 'text-muted-foreground'
                    )}
                    aria-label={`Save as ${option.label}`}
                    aria-pressed={saveAs === option.value}
                    onclick={() => onSaveAsChange(option.value)}
                >
                    <option.icon />
                    {option.label}
                </Button>
            {/each}
        </div>

        <div class="flex gap-1.5">
            <Button class="h-8 flex-1" disabled={!canSave} onclick={onSave}>Save</Button>
            <Button variant="outline" class="h-8 flex-1" onclick={onClear}>Clear</Button>
        </div>
    </div>
</div>
