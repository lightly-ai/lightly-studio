<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import SampleAnnotationRect from '$lib/components/SampleDetails/SampleAnnotationRect/SampleAnnotationRect.svelte';
    import AnnotationPreview from '$lib/components/SampleDetails/AnnotationPreview/AnnotationPreview.svelte';
    import NormalizedBoxRect from '$lib/components/SampleDetails/NormalizedBoxRect/NormalizedBoxRect.svelte';
    import SmartSelectPoints from './SmartSelectPoints.svelte';
    import { useDragBox } from '$lib/components/SampleDetails/useDragBox/useDragBox.svelte';
    import type { useSmartSelect } from './useSmartSelect.svelte';

    type SaveAs = ComponentProps<typeof AnnotationPreview>['saveAs'];

    interface Props {
        sample: { width: number; height: number };
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
        scale,
        isPanning,
        interactionRect = $bindable(),
        saveAs,
        smartSelect
    }: Props = $props();

    let excluding = $state(false);
    const exclusionCursor =
        "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24'%3E%3Ccircle cx='12' cy='12' r='9' fill='%23e11d48' stroke='white' stroke-width='2'/%3E%3Cpath d='M7 12h10' stroke='white' stroke-width='2'/%3E%3C/svg%3E\") 12 12, crosshair";
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
        smartSelect.addPoint(point);
    };

    // Bound to the image, so keys on other controls keep their default action.
    const onKeyDown = (event: KeyboardEvent) => {
        if (event.key === 'Enter' && smartSelect.canSave) {
            event.preventDefault();
            save();
        } else if (event.key === 'Escape') {
            if (smartSelect.points.length === 0 && !smartSelect.box && !smartSelect.preview) return;
            // Clears the prompts first, so the next press closes the tool.
            event.stopPropagation();
            smartSelect.clear();
        }
    };
</script>

<svelte:window
    onkeydown={(event) => (excluding = event.shiftKey)}
    onkeyup={(event) => (excluding = event.shiftKey)}
    onpointermove={(event) => (excluding = event.shiftKey)}
    onblur={() => (excluding = false)}
/>

{#if smartSelect.preview}
    <AnnotationPreview preview={smartSelect.preview} image={sample} {saveAs} />
{/if}
{#if drag.box || smartSelect.box}
    <NormalizedBoxRect box={(drag.box ?? smartSelect.box)!} image={sample} dashed />
{/if}
<SmartSelectPoints points={smartSelect.points} image={sample} {scale} />
<SampleAnnotationRect
    bind:interactionRect
    {sample}
    cursor={excluding ? exclusionCursor : 'crosshair'}
    pointerEvents={isPanning || smartSelect.isPending || smartSelect.isSaving ? 'none' : 'all'}
    onpointerdown={drag.onPointerDown}
    onpointermove={drag.onPointerMove}
    onpointerup={onPointerUp}
    onpointercancel={drag.onPointerCancel}
    onkeydown={onKeyDown}
/>
