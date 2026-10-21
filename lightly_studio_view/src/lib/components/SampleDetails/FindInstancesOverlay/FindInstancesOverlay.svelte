<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import InstanceDeleteButton from './InstanceDeleteButton.svelte';
    import { useFindInstances } from './useFindInstances.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        collectionId: string;
        sampleId: string;
        sample: { width: number; height: number };
        interactionRect?: SVGRectElement | null;
        refetch: () => void;
        prompt: string;
        onPromptChange: (prompt: string) => void;
        maxInstances: number;
        saveAs: SaveAs;
        annotationClass?: string | null;
        annotationSource?: string | null;
        isDrawingBox: boolean;
        onBoxDrawn: () => void;
        onStateChange: (state: {
            boxCount: number;
            isGenerating: boolean;
            resultCount: number;
            canSave: boolean;
            generate: () => void;
            save: () => void;
            clear: () => void;
        }) => void;
    }

    let {
        collectionId,
        sampleId,
        sample,
        interactionRect = $bindable(),
        refetch,
        prompt,
        onPromptChange,
        maxInstances,
        saveAs,
        annotationClass,
        annotationSource,
        isDrawingBox,
        onBoxDrawn,
        onStateChange
    }: Props = $props();

    const instances = useFindInstances(() => ({
        collectionId,
        sampleId,
        prompt,
        maxInstances,
        saveAs,
        annotationClass,
        annotationSource,
        onSaved: refetch
    }));
    const drag = useDragBox(() => ({ interactionRect }));

    const clear = () => {
        instances.clear();
        onPromptChange('');
    };

    $effect(() => {
        onStateChange({
            boxCount: instances.boxes.length,
            isGenerating: instances.isGenerating,
            resultCount: instances.predictions.length,
            canSave: instances.canSave,
            generate: () => void instances.generate(),
            save: () => void instances.save(),
            clear
        });
    });

    const onPointerUp = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const { box } = drag.onPointerUp(event);
        if (box) instances.addBox(box);
        onBoxDrawn();
    };
</script>

{#each instances.predictions as preview, index (index)}
    <AnnotationPreview {preview} image={sample} {saveAs} />
{/each}
{#if drag.box}
    <NormalizedBoxRect box={drag.box} image={sample} dashed />
{/if}
{#each instances.boxes as box, index (index)}
    <NormalizedBoxRect {box} image={sample} />
{/each}
{#if isDrawingBox}
    <SampleAnnotationRect
        bind:interactionRect
        {sample}
        cursor="crosshair"
        onpointerdown={drag.onPointerDown}
        onpointermove={drag.onPointerMove}
        onpointerup={onPointerUp}
        onpointercancel={(event) => {
            drag.onPointerCancel(event);
            onBoxDrawn();
        }}
    />
{/if}
{#each instances.predictions as preview, index (index)}
    <InstanceDeleteButton
        bbox={preview.bbox}
        {index}
        onDelete={() => instances.removePrediction(preview)}
    />
{/each}
