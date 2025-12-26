<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import {
        type AnnotationView,
        type CaptionView,
        type TagView
    } from '$lib/api/lightly_studio_local';
    import type { ListItem } from '$lib/components/SelectList/types';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';
    import SampleDetailsAnnotationSegment from '../SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';
    import { type Snippet } from 'svelte';

    type Props = {
        sample: {
            annotations: AnnotationView[];
            captions: CaptionView[] | undefined;
            sample_id: string;
            tags: TagView[] | undefined;
        };
        selectedAnnotationId?: string;
        onUpdate: () => void;
        onRemoveTag: (tagId: string) => void;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        annotationsIdsToHide: Set<string>;
        annotationType: string | null;
        collectionId: string;
        isPanModeEnabled: boolean;
        metadataItem: Snippet;
    };
    let {
        addAnnotationEnabled = $bindable(false),
        addAnnotationLabel = $bindable<ListItem | undefined>(undefined),
        annotationType = $bindable<string | null>(undefined),
        selectedAnnotationId = $bindable<string | null>(),
        annotationsIdsToHide = $bindable<Set<string>>(),
        sample,
        onUpdate,
        onRemoveTag,
        collectionId,
        isPanModeEnabled,
        metadataItem
    }: Props = $props();

    const tags = $derived(sample.tags.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-y-auto dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <SampleDetailsAnnotationSegment
                bind:annotationType
                bind:addAnnotationEnabled
                bind:addAnnotationLabel
                bind:selectedAnnotationId
                bind:annotationsIdsToHide
                {collectionId}
                {isPanModeEnabled}
                refetch={onUpdate}
                annotations={sample.annotations}
            />
            <SampleDetailsCaptionSegment
                {collectionId}
                refetch={onUpdate}
                captions={sample?.captions ?? []}
                sampleId={sample.sample_id}
            />
            {@render metadataItem()}
        </div>
    </CardContent>
</Card>
