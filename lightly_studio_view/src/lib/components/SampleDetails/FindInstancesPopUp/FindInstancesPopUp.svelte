<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import { AnnotationClassSelect } from '$lib/components/SampleDetails/AnnotationClassSelect';
    import {
        AnnotationToolPopUp,
        SaveAsToggle,
        SaveButtons
    } from '$lib/components/SampleDetails/AnnotationToolPopUp';
    import type { useFindInstances } from '$lib/components/SampleDetails/FindInstancesOverlay/useFindInstances.svelte';
    import InstancePromptInput from './InstancePromptInput/InstancePromptInput.svelte';
    import MaxInstancesInput from './MaxInstancesInput/MaxInstancesInput.svelte';

    type SaveAs = ComponentProps<typeof SaveAsToggle>['saveAs'];

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
        // Owned by the parent, so the overlay reads the same boxes and results.
        instances: ReturnType<typeof useFindInstances>;
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
        instances,
        onClear
    }: Props = $props();
</script>

<AnnotationToolPopUp title="Find all instances">
    <p class="text-xs text-muted-foreground">
        {#if instances.predictions.length > 0}
            Instances found: {instances.predictions.length}.
            {#if !annotationClass}Pick a class to save them.{/if}
        {:else if instances.isEmptyResult}
            No instances found. Try another prompt or draw boxes.
        {:else}
            {#if instances.boxes.length > 0}Boxes drawn: {instances.boxes.length}.{/if}
            {prompt.trim()
                ? 'Press Enter to search.'
                : 'Type a prompt. Draw boxes to show more examples.'}
        {/if}
    </p>
    <InstancePromptInput {prompt} {onPromptChange} {isDrawingBox} {onDrawBoxChange} {instances} />
    <MaxInstancesInput value={maxInstances} onChange={onMaxInstancesChange} />

    {#snippet saveControls()}
        <AnnotationClassSelect
            {collectionId}
            value={annotationClass}
            onChange={onAnnotationClassChange}
            label="Annotation class"
            className="h-8"
        />
        <SaveAsToggle {saveAs} {onSaveAsChange} />
        <SaveButtons
            canSave={instances.canSave}
            isSaving={instances.isSaving}
            onSave={() => void instances.save()}
            {onClear}
        />
    {/snippet}
</AnnotationToolPopUp>
