import { get, readonly, writable, type Readable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { createSplit } from '$lib/api/lightly_studio_local/sdk.gen';
import type { SplitCreateBody } from '$lib/api/lightly_studio_local/types.gen';
import type { TagView } from '$lib/services/types';

type SplitError = { error: string };

function extractError(error: unknown, fallback: string): string {
    return (error as SplitError)?.error || fallback;
}

interface UseCreateSplitParams {
    tags: Readable<TagView[]>;
    setTagSelected: (tagId: string, isSelected: boolean) => void;
    loadTags: () => Promise<void>;
    closeSplitDialog: () => void;
}

interface SubmitParams {
    collectionId: string;
    sizes: SplitCreateBody['sizes'];
    filter: SplitCreateBody['filter'];
}

export function useCreateSplit(params: UseCreateSplitParams) {
    const _isSubmitting = writable(false);

    async function submit(submitParams: SubmitParams): Promise<boolean> {
        if (get(_isSubmitting)) return false;
        const { collectionId, sizes, filter } = submitParams;
        _isSubmitting.set(true);

        try {
            // Omitting seed lets the backend pick a random seed for each split.
            const response = await createSplit({
                path: { collection_id: collectionId },
                body: { sizes, filter: filter ?? undefined }
            });

            if (response.error || !response.data) {
                toast.error(extractError(response.error, 'Failed to split dataset'));
                return false;
            }

            const summary = response.data.splits
                .map((split) => `${split.name}: ${split.count}`)
                .join(', ');
            toast.success(`Dataset split (seed ${response.data.seed}) — ${summary}`);

            await params.loadTags();
            selectSplitTags(
                get(params.tags),
                response.data.splits.map((split) => split.name),
                params.setTagSelected
            );
            params.closeSplitDialog();
            return true;
        } catch (error) {
            // API functions return { data, error } and don't throw, so this only
            // fires for unexpected runtime bugs in the hook itself.
            console.error('Unexpected error in useCreateSplit.submit:', error);
            toast.error('Failed to split dataset: ' + (error as Error).message);
            return false;
        } finally {
            _isSubmitting.set(false);
        }
    }

    return {
        isSubmitting: readonly(_isSubmitting),
        submit
    };
}

function selectSplitTags(
    tags: TagView[],
    splitNames: string[],
    setTagSelected: (tagId: string, isSelected: boolean) => void
): void {
    for (const name of splitNames) {
        const tag = tags.find((candidate) => candidate.name === name);
        if (tag) setTagSelected(tag.tag_id, true);
    }
}
