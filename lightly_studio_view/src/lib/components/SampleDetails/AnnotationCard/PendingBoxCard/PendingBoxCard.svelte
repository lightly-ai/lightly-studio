<script lang="ts">
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { usePendingBoxClass, useStickyClass } from '$lib/hooks';
    import { ClassSearchList, useClassSearchData } from '$lib/components/SampleDetails/SearchList';
    import { AnnotationCardFrame } from '../AnnotationCardFrame';
    import { CardCloseButton } from '../CardCloseButton';

    interface Props {
        /** The collection that owns the annotation classes. */
        collectionId: string;
        getLayer: () => SVGGraphicsElement | null;
    }

    const { collectionId, getLayer }: Props = $props();
    const { request, resolve, cancel } = usePendingBoxClass();
    const { context: toolbarContext } = useSampleDetailsToolbarContext();
    const { pickClass } = useStickyClass();
    const classSearch = useClassSearchData(() => collectionId);

    const pick = (className: string) => {
        pickClass(collectionId, className);
        resolve(className);
    };
    // A click anywhere outside the card drops the box, like Esc. Right and middle clicks and
    // Space-drag panning keep it.
    const handlePointerDownOutside = (event: PointerEvent) => {
        if (event.button !== 0 || toolbarContext.status === 'drag') return;
        cancel();
    };
    // Esc drops the box wherever the focus is, before the panel's Esc switches the tool.
    const handleWindowKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Escape' || !$request) return;
        event.stopPropagation();
        cancel();
    };
    // The card mounts hidden until it finds its place, and a hidden input can't take focus.
    const focusSearch = (card: HTMLElement) => card.querySelector('input')?.focus();
</script>

<svelte:window onkeydowncapture={handleWindowKeyDown} />

{#if $request}
    <AnnotationCardFrame
        bbox={$request.bbox}
        {getLayer}
        label="Annotation class for the new box"
        testId="pending-box-card"
        onShow={focusSearch}
        onPointerDownOutside={handlePointerDownOutside}
    >
        <div class="flex justify-end">
            <CardCloseButton onClose={cancel} />
        </div>
        <ClassSearchList
            names={classSearch.classNames}
            recent={classSearch.recent}
            onPick={pick}
            onCancel={cancel}
        />
    </AnnotationCardFrame>
{/if}
