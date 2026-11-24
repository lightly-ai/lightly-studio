<script lang="ts">
    import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';
    import { TagChips, TagsEditor } from '$lib/components';

    interface Props {
        /** Cuboid whose tags are shown. */
        cuboid: CuboidAnnotation;
        /** The selected cuboid gets add and remove controls; the others show read-only chips. */
        isSelected: boolean;
        /** Reloads the tick after a tag is added or removed. */
        onTagsChange?: () => void;
    }

    let { cuboid, isSelected, onTagsChange }: Props = $props();

    const tags = $derived(cuboid.tags ?? []);
</script>

<!-- A cuboid is a sample of its source collection on one frame, so it is tagged like one. -->
{#if isSelected}
    {#key cuboid.id}
        <TagsEditor
            class="flex flex-col gap-1 px-4 pb-2"
            {tags}
            collectionId={cuboid.annotationSourceId}
            sampleId={cuboid.id}
            onRefetch={onTagsChange}
        />
    {/key}
{:else if tags.length > 0}
    <div class="px-4 pb-2" data-testid="point-cloud-annotation-tags">
        <TagChips {tags} />
    </div>
{/if}
