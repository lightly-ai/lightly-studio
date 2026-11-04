<script lang="ts">
    import { X } from '@lucide/svelte';
    import { useSampleDetailsToolbarContext } from '$lib/contexts/SampleDetailsToolbar.svelte';
    import { useRecentClasses, useStickyClass } from '$lib/hooks';
    import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
    import { usePendingBoxClass } from '$lib/hooks/usePendingBoxClass/usePendingBoxClass';
    import ClassSearchList from '../ClassSearchList/ClassSearchList.svelte';
    import AnnotationCardFrame from './AnnotationCardFrame.svelte';

    interface Props {
        /** The collection that owns the annotation classes. */
        collectionId: string;
        getLayer: () => SVGGraphicsElement | null;
    }

    const { collectionId, getLayer }: Props = $props();
    const { request, resolve, cancel } = usePendingBoxClass();
    const { context: toolbarContext } = useSampleDetailsToolbarContext();
    const { pickClass } = useStickyClass();
    const { recentClasses } = useRecentClasses();
    const labels = useAnnotationLabels(() => ({ collectionId }));

    // Stable arrays: the list resets its first-row highlight when these change identity.
    const classNames = $derived((labels.data ?? []).map((l) => l.annotation_label_name));
    const recent = $derived($recentClasses[collectionId] ?? []);

    let body: HTMLDivElement | undefined = $state();

    const pick = (className: string) => {
        pickClass(collectionId, className);
        resolve(className);
    };
    // A click anywhere outside the card drops the box, like Esc. Right and middle clicks and
    // Space-drag panning keep it.
    const handleWindowPointerDown = (event: PointerEvent) => {
        if (event.button !== 0 || toolbarContext.status === 'drag') return;
        const card = body?.parentElement;
        if (card && event.target instanceof Node && card.contains(event.target)) return;
        cancel();
    };
    // Esc drops the box wherever the focus is, before the panel's Esc switches the tool.
    const handleWindowKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Escape' || !$request) return;
        event.stopPropagation();
        cancel();
    };
    // The card mounts hidden until it finds its place, and a hidden input can't take focus.
    const focusSearch = () => body?.querySelector('input')?.focus();
</script>

<svelte:window onpointerdown={handleWindowPointerDown} onkeydowncapture={handleWindowKeyDown} />

{#if $request}
    <AnnotationCardFrame
        bbox={$request.bbox}
        {getLayer}
        testId="pending-box-card"
        onShow={focusSearch}
    >
        <div bind:this={body} class="contents">
            <div class="flex justify-end">
                <button
                    type="button"
                    class="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
                    aria-label="Close"
                    title="Close (Esc)"
                    onclick={cancel}
                >
                    <X class="size-4" />
                </button>
            </div>
            <ClassSearchList names={classNames} {recent} onPick={pick} onCancel={cancel} />
        </div>
    </AnnotationCardFrame>
{/if}
