import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { get, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { splitDatasetMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useGlobalStorage, useImageFilters, useTags, useVideoFilters } from '$lib/hooks';

interface Options {
    collectionId: string;
    sampleType: 'image' | 'video';
    onClose: () => void;
}

export function useDatasetSplit(getOptions: () => Options) {
    const { collectionId, sampleType, onClose } = getOptions();
    const client = useQueryClient();
    const mutation = createMutation(() => splitDatasetMutation());
    const { tags, loadTags } = useTags({ collection_id: collectionId });
    const { filteredSampleCount } = useGlobalStorage();
    // Capture once per opening so later filter changes cannot alter the submitted scope.
    const filter = structuredClone(
        sampleType === 'image'
            ? { ...get(useImageFilters().imageFilter), filter_type: 'image' as const }
            : { ...get(useVideoFilters().videoFilter), filter_type: 'video' as const }
    );
    const sampleCount = get(filteredSampleCount);
    const pending = writable(false);
    const error = writable<string | undefined>();

    async function submit(
        values: Omit<Parameters<typeof mutation.mutateAsync>[0]['body'], 'filter'>
    ) {
        if (get(pending)) return;
        pending.set(true);
        error.set(undefined);
        try {
            const counts = await mutation.mutateAsync({
                path: { collection_id: collectionId },
                body: { ...values, filter }
            });
            // Tags have a separate store; refresh both it and queries that may depend on tags.
            await Promise.all([loadTags(), client.invalidateQueries()]);
            toast.success(
                counts
                    .map(({ tag_name, sample_count }) => `${tag_name}: ${sample_count}`)
                    .join(', ')
            );
            onClose();
        } catch {
            error.set('Unable to split dataset. Please try again.');
        } finally {
            pending.set(false);
        }
    }

    return { sampleCount, tags, pending, error, submit };
}
