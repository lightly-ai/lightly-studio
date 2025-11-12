import { type UpdateCaptionTextData } from '$lib/api/lightly_studio_local';
import {
    getCaptionOptions,
    updateCaptionTextMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

export const useCaption = ({
    datasetId,
    captionId,
    onUpdate
}: {
    datasetId: string;
    captionId: string;
    onUpdate?: () => void;
}) => {
    const captionOptions = getCaptionOptions({
        path: {
            caption_id: captionId,
            dataset_id: datasetId
        }
    });
    const client = useQueryClient();

    const captionMutation = createMutation(updateCaptionTextMutation());
    captionMutation.subscribe(() => undefined);

    const mutateCaptionText = (text: string) =>
        new Promise<void>((resolve, reject) => {
            get(captionMutation).mutate(
                {
                    path: {
                        dataset_id: datasetId,
                        caption_id: captionId
                    } as UpdateCaptionTextData['path'],
                    body: text
                },
                {
                    onSuccess: () => resolve(),
                    onError: (error) => reject(error)
                }
            );
        });

    const caption = createQuery(captionOptions);

    const refetch = async () => {
        await client.invalidateQueries({ queryKey: captionOptions.queryKey });
    };

    const updateCaptionText = async (text: string) => {
        try {
            await mutateCaptionText(text);
            await refetch();
            toast.success('Caption updated successfully');
            onUpdate?.();
        } catch (error: unknown) {
            toast.error('Failed to update caption: ' + (error as Error).message);
        }
    };
    return {
        updateCaptionText,
        caption,
        refetch
    };
};
