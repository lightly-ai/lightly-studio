<script lang="ts">
    import { Card, CardContent } from '$lib/components';
    import AnnotationMetadata from './AnnotationMetadata/AnnotationMetadata.svelte';
    import { useRemoveTagFromAnnotation } from '$lib/hooks/useRemoveTagFromAnnotation/useRemoveTagFromAnnotation';
    import SegmentTags from '../../SegmentTags/SegmentTags.svelte';
    import { type AnnotationView } from '$lib/api/lightly_studio_local';
    import type { Snippet } from 'svelte';

    const {
        annotation,
        onUpdate,
        sampleDetails
    }: {
        annotation: AnnotationView;
        onUpdate: () => void;
        sampleDetails: Snippet;
    } = $props();
    const { removeTagFromAnnotation } = useRemoveTagFromAnnotation();

    const tags = $derived(annotation.tags?.map((t) => ({ tagId: t.tag_id, name: t.name })) ?? []);

    const onRemoveTag = async (tagId: string) => {
        await removeTagFromAnnotation(annotation.sample_id, tagId);
    };
</script>

<Card className="h-full">
    <CardContent className="h-full flex flex-col">
        <div
            class="flex h-full min-h-0 flex-col space-y-4 overflow-hidden dark:[color-scheme:dark]"
        >
            <SegmentTags {tags} onClick={onRemoveTag} />
            <AnnotationMetadata {annotation} {onUpdate} />

            {@render sampleDetails()}
        </div>
    </CardContent>
</Card>
