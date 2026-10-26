<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import InstanceDeleteButton from './InstanceDeleteButton/InstanceDeleteButton.svelte';
    import type { useFindInstances } from './useFindInstances.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
        scale: number;
        interactionRect?: SVGRectElement | null;
        saveAs: SaveAs;
        isDrawingBox: boolean;
        onDrawEnd: () => void;
        // Owned by the parent, so the pop-up reads the same boxes and results.
        instances: ReturnType<typeof useFindInstances>;
    }

    let {
        sample,
        scale,
        interactionRect = $bindable(),
        saveAs,
        isDrawingBox,
        onDrawEnd,
        instances
    }: Props = $props();

    const drag = useDragBox(() => ({ interactionRect }));

    const onPointerUp = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const { box } = drag.onPointerUp(event);
        // A click without a drag keeps the tool open.
        if (!box) return;
        instances.addBox(box);
        onDrawEnd();
    };

    const onPointerCancel = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        drag.onPointerCancel(event);
        onDrawEnd();
    };
</script>

{#each instances.predictions as preview (preview)}
    <AnnotationPreview {preview} image={sample} {saveAs} />
{/each}
{#if drag.box}
    <NormalizedBoxRect box={drag.box} image={sample} dashed />
{/if}
{#each instances.boxes as box (box)}
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
        onpointercancel={onPointerCancel}
    />
{/if}
<!-- After the interaction rect, so the delete buttons stay clickable. -->
{#each instances.predictions as preview, index (preview)}
    <InstanceDeleteButton
        bbox={preview.bbox}
        {index}
        {scale}
        disabled={instances.isSaving}
        onDelete={() => instances.removePrediction(preview)}
    />
{/each}
