<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import SampleMetadata from '$lib/components/SampleMetadata/SampleMetadata.svelte';
    import { type ImageView } from '$lib/api/lightly_studio_local';
    import type { ListItem } from '$lib/components/SelectList/types';
    import SegmentTags from '$lib/components/SegmentTags/SegmentTags.svelte';
    import SampleDetailsAnnotationSegment from '../SampleDetailsAnnotationSegment/SampleDetailsAnnotationSegment.svelte';
    import SampleDetailsCaptionSegment from '../SampleDetailsCaptionsSegment/SampleDetailsCaptionSegment.svelte';

    type Props = {
        sample: ImageView;
        selectedAnnotationId?: string;
        onUpdate: () => void;
        onRemoveTag: (tagId: string) => void;
        addAnnotationEnabled: boolean;
        addAnnotationLabel: ListItem | undefined;
        annotationsIdsToHide: Set<string>;
        annotationType: string | null;
        collectionId: string;
        isPanModeEnabled: boolean;
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
        isPanModeEnabled
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
            <SampleMetadata {sample} />
        </div>
    </CardContent>
</Card>
