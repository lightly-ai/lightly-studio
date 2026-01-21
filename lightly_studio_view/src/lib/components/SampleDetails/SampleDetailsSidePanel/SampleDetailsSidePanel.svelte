<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import {
        type AnnotationView,
        type CaptionView,
        type TagView
    } from '$lib/api/lightly_studio_local';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';
    import SampleDetailsAnnotationSegment from '../SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import SampleDetailsClassificationSegment from '../SampleDetailsClassificationSegment/SampleDetailsClassificationSegment.svelte';
    import { type Snippet } from 'svelte';
    import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';

    type Props = {
        sample: {
            annotations: AnnotationView[];
            captions: CaptionView[] | undefined;
            sample_id: string;
            tags: TagView[] | undefined;
        };
        onUpdate: () => void;
        onRemoveTag: (tagId: string) => void;
        annotationsIdsToHide: Set<string>;
        collectionId: string;
        isPanModeEnabled: boolean;
        metadataItem?: Snippet | undefined;
    };
    let {
        annotationsIdsToHide = $bindable<Set<string>>(),
        sample,
        onUpdate,
        onRemoveTag,
        collectionId,
        isPanModeEnabled,
        metadataItem
    }: Props = $props();

    const tags = $derived(sample.tags.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);
    const { context: annotationLabelContext } = useAnnotationLabelContext();

    // Auto-scroll to selected annotation
    $effect(() => {
        // Auto-scroll if annotations have changed
        void sample.annotations;
        const annotationId =
            annotationLabelContext.annotationId ?? annotationLabelContext.lastCreatedAnnotationId;
        if (annotationId) {
            const element = document.querySelector(`button[data-annotation-id="${annotationId}"]`);
            if (element) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest',
                    inline: 'nearest'
                });
            }
        }
    });
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-y-auto dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <SampleDetailsAnnotationSegment
                bind:annotationsIdsToHide
                {collectionId}
                {isPanModeEnabled}
                refetch={onUpdate}
                annotations={sample.annotations}
            />
            <SampleDetailsClassificationSegment
                {collectionId}
                refetch={onUpdate}
                annotations={sample.annotations}
                sampleId={sample.sample_id}
            />
            <SampleDetailsCaptionSegment
                {collectionId}
                refetch={onUpdate}
                captions={sample?.captions ?? []}
                sampleId={sample.sample_id}
            />
            {#if metadataItem}
                {@render metadataItem()}
            {/if}
        </div>
    </CardContent>
</Card>
