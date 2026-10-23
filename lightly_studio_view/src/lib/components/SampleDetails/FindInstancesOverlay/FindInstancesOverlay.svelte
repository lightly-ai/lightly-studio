<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import InstanceDeleteButton from './InstanceDeleteButton.svelte';
    import type { useFindInstances } from './useFindInstances.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
        interactionRect?: SVGRectElement | null;
        saveAs: SaveAs;
        isDrawingBox: boolean;
        onBoxDrawn: () => void;
        // Owned by the parent, so the pop-up reads the same boxes and results.
        instances: ReturnType<typeof useFindInstances>;
    }

    let {
        sample,
        interactionRect = $bindable(),
        saveAs,
        isDrawingBox,
        onBoxDrawn,
        instances
    }: Props = $props();

    const drag = useDragBox(() => ({ interactionRect }));

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
