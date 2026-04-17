<script lang="ts">
    import { Checkbox } from '$lib/components';
    import type { GridType } from '$lib/types';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { Tags as Tagsicon } from '@lucide/svelte';
    import type { TagView } from '$lib/services/types';
    import { useTags } from '$lib/hooks/useTags/useTags.js';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { createTag, addSampleIdsToTagId } from '$lib/api/lightly_studio_local';
    import TagAssignInput from './TagAssignInput.svelte';
    import { toast } from 'svelte-sonner';

    let { collection_id, gridType }: Parameters<typeof useTags>[0] & { gridType: GridType } =
        $props();

    const tagKind = $derived(gridType === 'annotations' ? 'annotation' : 'sample');

    const { tags, tagsSelected, tagSelectionToggle, loadTags } = $derived(
        useTags({ collection_id, kind: [tagKind] })
    );

    const { getSelectedSampleIds, selectedSampleAnnotationCropIds } = useGlobalStorage();

    const selectedSampleIds = $derived(getSelectedSampleIds(collection_id));
    const hasSelection = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id]?.size ?? 0) > 0
            : $selectedSampleIds.size > 0
    );
    const selectedIds = $derived(
        tagKind === 'annotation'
            ? ($selectedSampleAnnotationCropIds[collection_id] ?? new Set<string>())
            : $selectedSampleIds
    );

    // ── Selection assignment ─────────────────────────────────────────────────────
    let assignBusy = $state(false);

    async function handleAssign(name: string) {
        assignBusy = true;
        try {
            const existingTag = $tags.find(
                (t: TagView) => t.name.toLowerCase() === name.toLowerCase()
            );
            if (existingTag) {
                const response = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: existingTag.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (response.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            } else {
                const createResponse = await createTag({
                    path: { collection_id },
                    body: { name, description: `${name} description`, kind: tagKind }
                });
                if (createResponse.error || !createResponse.data?.tag_id) {
                    toast.error('Failed to create tag. Please try again.');
                    return;
                }
                const assignResponse = await addSampleIdsToTagId({
                    path: { collection_id, tag_id: createResponse.data.tag_id },
                    body: { sample_ids: [...selectedIds] }
                });
                if (assignResponse.error) {
                    toast.error('Failed to assign tag. Please try again.');
                    return;
                }
            }
            loadTags();
        } catch (error) {
            console.error('Failed to assign tag', error);
            toast.error('Failed to assign tag. Please try again.');
        } finally {
            assignBusy = false;
        }
    }
</script>

<Segment title="Tags" icon={Tagsicon}>
    <div class="mb-3 w-full space-y-1">
        <div class="space-y-1">
            {#each $tags as tag (tag.tag_id)}
                <div class="flex items-center py-0.5" data-testid="tag-menu-item">
                    <Checkbox
                        name={tag.tag_id}
                        isChecked={$tagsSelected.has(tag.tag_id)}
                        label={tag.name}
                        onCheckedChange={() => tagSelectionToggle(tag.tag_id)}
                    />
                </div>
            {:else}
                <p>No tags yet</p>
            {/each}
        </div>

        <TagAssignInput
            options={$tags}
            busy={assignBusy || !hasSelection}
            onSelect={handleAssign}
        />
    </div>
</Segment>
