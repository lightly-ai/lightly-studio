import { type UpdateCaptionTextData } from '$lib/api/lightly_studio_local';
import {
    getCaptionOptions,
    updateCaptionTextMutation
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

export const useCaption = ({ sampleId, onUpdate }: { sampleId: string; onUpdate?: () => void }) => {
    const captionOptions = getCaptionOptions({
        path: {
            sample_id: sampleId
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
                        sample_id: sampleId
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
