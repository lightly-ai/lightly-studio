<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { AnnotationView } from '$lib/api/lightly_studio_local';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import SmartSelectPoints from './SmartSelectPoints.svelte';
    import { getClassNameAtPoint } from './SmartSelectOverlay.helpers';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import type { useSmartSelect } from './useSmartSelect.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
        // Visible annotations, so the class hint never comes from a hidden one.
        annotations: AnnotationView[];
        scale: number;
        // Lets pan events through while keeping the prompts.
        isPanning: boolean;
        interactionRect?: SVGRectElement | null;
        saveAs: SaveAs;
        // Owned by the parent, so the pop-up reads the same prompts.
        smartSelect: ReturnType<typeof useSmartSelect>;
    }

    let {
        sample,
        annotations,
        scale,
        isPanning,
        interactionRect = $bindable(),
        saveAs,
        smartSelect
    }: Props = $props();

    const drag = useDragBox(() => ({ interactionRect }));
    const save = () => void smartSelect.save();

    const onPointerUp = (event: PointerEvent & { currentTarget: SVGRectElement }) => {
        const { start, box } = drag.onPointerUp(event);
        if (box) {
            smartSelect.selectBox(box);
            return;
        }
        if (!start) return;
        // Shift-click adds a negative point.
        const point = { ...start, positive: !event.shiftKey };
        smartSelect.addPoint(point, getClassNameAtPoint(annotations, point, sample));
    };

    // Bound to the image, so keys on other controls keep their default action.
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter' && smartSelect.canSave) {
            event.preventDefault();
            save();
        } else if (event.key === 'Escape') {
            if (smartSelect.points.length === 0 && !smartSelect.preview) return;
            // Clears the prompts first, so the next press closes the tool.
            event.stopPropagation();
            smartSelect.clear();
        }
    };
</script>

{#if smartSelect.preview}
    <AnnotationPreview preview={smartSelect.preview} image={sample} {saveAs} />
{/if}
{#if drag.box}
    <NormalizedBoxRect box={drag.box} image={sample} dashed />
{/if}
<SmartSelectPoints points={smartSelect.points} image={sample} {scale} />
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor="crosshair"
    pointerEvents={isPanning ? 'none' : 'all'}
    onpointerdown={drag.onPointerDown}
    onpointermove={drag.onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={drag.onPointerCancel}
    onkeydown={onKeyDown}
/>
